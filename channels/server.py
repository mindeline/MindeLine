"""WhatsApp menu and public Android fallback. Single-process, temporary deduplication."""
import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import html
import json
import os
import re
import time
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

MAX_BODY=128*1024
PACKAGE='app.mindeline.mobile'

def https_url(value, *, origin=False):
    p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment or p.query:
        raise ValueError('An HTTPS URL without credentials, query or fragment is required')
    if p.port not in (None,443) or p.hostname in {'localhost','127.0.0.1'}:
        raise ValueError('A public HTTPS URL is required')
    if origin and p.path not in ('','/'):
        raise ValueError('Gateway URL must be an origin, without a path')
    if p.hostname.endswith('.invalid'): raise ValueError('Replace placeholder URLs')
    return value.rstrip('/')

@dataclass(frozen=True)
class Config:
    mode: str='preview'
    web_url: str=''
    gateway_url: str=''
    apk_url: str=''
    demo_web_url: str=''
    verify_token: str=''
    app_secret: str=''
    access_token: str=''
    phone_id: str=''
    graph_version: str=''
    certificate: str=''

    @classmethod
    def from_env(cls):
        c=cls(mode=os.getenv('CHANNEL_MODE','preview'),web_url=os.getenv('MINDELINE_WEB_URL',''),
              gateway_url=os.getenv('MINDELINE_GATEWAY_URL',''),apk_url=os.getenv('MINDELINE_APK_URL',''),
              demo_web_url=os.getenv('MINDELINE_DEMO_WEB_URL',''),
              verify_token=os.getenv('WHATSAPP_VERIFY_TOKEN',''),app_secret=os.getenv('META_APP_SECRET',''),
              access_token=os.getenv('WHATSAPP_ACCESS_TOKEN',''),phone_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID',''),
              graph_version=os.getenv('META_GRAPH_VERSION',''),certificate=os.getenv('ANDROID_SHA256',''))
        c.validate(); return c

    def validate(self):
        if self.mode not in {'preview','live'}:raise ValueError('Invalid channel mode')
        for value in (self.web_url,self.apk_url):
            if value:https_url(value)
        if self.gateway_url:https_url(self.gateway_url,origin=True)
        if self.demo_web_url:
            p=urlsplit(self.demo_web_url)
            if (self.mode!='preview' or p.scheme!='http' or p.hostname not in {'127.0.0.1','::1'}
                    or p.port is None or p.path not in ('','/') or p.username or p.password or p.query or p.fragment):
                raise ValueError('Demo web URL must be a local loopback URL in preview mode')
        if self.certificate and not re.fullmatch(r'(?:[A-Fa-f0-9]{2}:){31}[A-Fa-f0-9]{2}',self.certificate):
            raise ValueError('Invalid Android SHA-256 certificate fingerprint')
        if self.mode=='live':
            if not all([self.web_url,self.gateway_url,self.verify_token,self.app_secret,self.access_token,self.phone_id,self.graph_version]):
                raise ValueError('Live mode requires configured URLs and Meta credentials')
            if len(self.verify_token)<24:raise ValueError('Use a long random webhook verification token')
            if not self.phone_id.isdigit() or not re.fullmatch(r'v\d+\.\d+',self.graph_version):
                raise ValueError('Invalid Graph API version or phone ID')


def valid_signature(body, signature, secret):
    if not secret or not isinstance(signature,str):return False
    expected='sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)


def message_payload(sender, text):
    base={'messaging_product':'whatsapp','recipient_type':'individual','to':sender}
    return dict(base,type='text',text={'preview_url':False,'body':text})


def buttons_payload(sender, text, choices):
    base={'messaging_product':'whatsapp','recipient_type':'individual','to':sender}
    return dict(base,type='interactive',interactive={
        'type':'button','body':{'text':text},
        'action':{'buttons':[{'type':'reply','reply':{'id':choice,'title':title}}
                             for choice,title in choices]}})


FLOW_CHOICES={
    'mood':(('mood_good','😄 Bien'),('mood_ok','😐 Más o menos'),('mood_bad','😟 Mal')),
    'medication':(('med_yes','Sí'),('med_no','No'),('med_sometimes','A veces')),
    'appointment':(('appointment_yes','Sí'),('appointment_no','No puedo asistir')),
    'nursing':(('nursing_yes','Sí, por favor'),('nursing_no','No, gracias')),
    'destination':(('web','Abrir web'),('android','Abrir app Android')),
    'consent':(('consent_accept','Acepto y continuar'),('consent_decline','No acepto')),
}
FLOW_QUESTIONS={
    'mood':'Hola 👋 Soy el bot de MindeLine. ¿Cómo te sientes hoy? Elige un emoji para continuar.\n'
          'Esto es un prototipo, no una evaluación clínica. No ingreses datos reales. '
          'MindeLine no guarda tus respuestas; WhatsApp/Meta procesa tus mensajes según sus condiciones. '
          'Si estás en peligro inmediato, contacta los servicios de emergencia locales.',
    'medication':'1 de 3 · ¿Tomaste tu medicación como fue indicada?',
    'appointment':'2 de 3 · ¿Podrás asistir a tu próxima cita?',
    'nursing':'3 de 3 · ¿Quieres hablar con enfermería?',
    'destination':'Gracias por responder. ¿Cómo quieres continuar?',
    'consent':'Antes de continuar: en un servicio real, tus respuestas podrían conservarse y ser '
              'consultadas por profesionales de salud autorizados y asignados para atenderte. '
              'Aceptar aquí solo simula tu decisión en este prototipo: no crea una cuenta ni guarda '
              'o comparte el chat. No es consentimiento informado ni una firma legal. '
              'Si aceptas, te enviaremos el enlace para solicitar acceso; el equipo debe habilitar '
              'la cuenta. Puedes rechazar sin continuar.',
}
FLOW_ORDER=('mood','medication','appointment','nursing','destination')


def flow_prompt(sender, phase, reminder=False):
    text=FLOW_QUESTIONS[phase]
    if reminder:
        text='Elige una de las opciones para seguir.\n'+text
    return buttons_payload(sender,text,FLOW_CHOICES[phase])


def reply_payload(sender, choice, config):
    if choice=='web':
        return message_payload(sender,'Abre MindeLine en la web y contacta al equipo para solicitar '
            'una cuenta:\n'+config.web_url+
            '\nEl equipo debe revisar y habilitar tu acceso. Este enlace no registra ni inicia sesión automáticamente.')
    if choice=='android':
        return message_payload(sender,'Abre MindeLine para Android:\n'+config.gateway_url+'/open'+
            '\nContacta al equipo para solicitar una cuenta; debe revisar y habilitar tu acceso. '
            'Si no tienes la app, el enlace mostrará las opciones disponibles.')
    return flow_prompt(sender,'mood')


def _normalized_text(value):
    return re.sub(r'\s+',' ',value.strip().casefold())


def _choice_for(phase, raw):
    if raw in {choice for choice,_ in FLOW_CHOICES[phase]}:
        return raw
    if phase=='mood':
        return {'😄':'mood_good','😄 bien':'mood_good','bien':'mood_good',
                '😐':'mood_ok','😐 más o menos':'mood_ok','más o menos':'mood_ok',
                'mas o menos':'mood_ok','😟':'mood_bad','😟 mal':'mood_bad','mal':'mood_bad'}.get(
                    _normalized_text(raw))
    if phase=='medication':
        return {'sí':'med_yes','si':'med_yes','no':'med_no','a veces':'med_sometimes',
                'aveces':'med_sometimes'}.get(_normalized_text(raw))
    if phase=='appointment':
        return {'sí':'appointment_yes','si':'appointment_yes','no':'appointment_no',
                'no puedo asistir':'appointment_no'}.get(_normalized_text(raw))
    if phase=='nursing':
        return {'sí':'nursing_yes','si':'nursing_yes','sí, por favor':'nursing_yes',
                'si por favor':'nursing_yes','no':'nursing_no','no, gracias':'nursing_no',
                'no gracias':'nursing_no'}.get(_normalized_text(raw))
    if phase=='destination':
        return {'web':'web','1':'web','android':'android','app':'android','2':'android'}.get(
            _normalized_text(raw))
    if phase=='consent':
        return {'acepto':'consent_accept','acepto y continuar':'consent_accept',
                'si':'consent_accept','sí':'consent_accept',
                'no acepto':'consent_decline','rechazar':'consent_decline',
                'no':'consent_decline'}.get(_normalized_text(raw))
    return None


def incoming_events(payload,config):
    if not isinstance(payload,dict) or payload.get('object')!='whatsapp_business_account':return []
    found=[]
    for entry in payload.get('entry',[]):
        for change in entry.get('changes',[]):
            value=change.get('value',{})
            if change.get('field')!='messages' or value.get('metadata',{}).get('phone_number_id')!=config.phone_id:continue
            for msg in value.get('messages',[]):
                sender,mid=msg.get('from',''),msg.get('id','')
                try:age=time.time()-int(msg.get('timestamp',0))
                except (TypeError,ValueError):continue
                if not isinstance(sender,str) or not re.fullmatch(r'\d{6,20}',sender):continue
                if not isinstance(mid,str) or not 1<=len(mid)<=256 or not -300<=age<23*3600:continue
                if msg.get('type')=='interactive':
                    raw=msg.get('interactive',{}).get('button_reply',{}).get('id','')
                elif msg.get('type')=='text':
                    raw=msg.get('text',{}).get('body','')
                elif msg.get('type')=='audio':
                    raw='__unsupported_audio__'
                else:
                    continue
                if not isinstance(raw,str):continue
                found.append((hashlib.sha256(mid.encode()).hexdigest(),sender,raw))
    return found


def events(payload,config):
    """Compatibility helper that previews the initial response for parsed messages."""
    return [(key,reply_payload(sender,raw if raw in {'web','android'} else '',config))
            for key,sender,raw in incoming_events(payload,config)]


def advance_flow(sender, raw, config, sessions):
    if raw=='__unsupported_audio__':
        return message_payload(sender,'Por ahora solo puedo responder mensajes escritos y opciones con botones. '
            'No escucho ni guardo audios; envíame tu respuesta por escrito o elige una opción.')
    now=time.monotonic()
    for session_key,(_,expires,_) in list(sessions.items()):
        if expires<=now:sessions.pop(session_key)
    key=hashlib.sha256(sender.encode()).hexdigest()
    if key not in sessions and len(sessions)>=5000:
        return message_payload(sender,'No es posible iniciar otra conversación ahora. Inténtalo más tarde.')
    phase,_,destination=sessions.get(key,('mood',0,None))
    choice=_choice_for(phase,raw)
    if phase=='destination' and choice in {'web','android'}:
        sessions[key]=('consent',now+30*60,choice)
        return flow_prompt(sender,'consent')
    if phase=='consent':
        sessions.pop(key,None)
        if choice=='consent_accept':
            return reply_payload(sender,destination,config)
        if choice=='consent_decline':
            return message_payload(sender,'No se continuará con el registro. El prototipo no guardó '
                'ni compartió tus respuestas. Gracias por participar.')
    if not choice:
        sessions[key]=(phase,now+30*60,destination)
        return flow_prompt(sender,phase,reminder=True)
    next_phase=FLOW_ORDER[FLOW_ORDER.index(phase)+1]
    sessions[key]=(next_phase,now+30*60,None)
    return flow_prompt(sender,next_phase)


STYLE='''body{margin:0;background:#f4f6fa;color:#192436;font:17px system-ui;line-height:1.6}main{max-width:520px;margin:9vh auto;padding:32px;background:white;border:1px solid #dde2ea;border-radius:20px}h1{font-size:32px;margin:0}small{color:#5b6475}a{display:block;padding:14px 20px;margin:12px 0;background:#237873;color:white;text-decoration:none;border-radius:10px;font-weight:600}.secondary{background:#e4e9f1;color:#192436}.note{font-size:14px;color:#5b6475}@media(max-width:600px){main{margin:20px;padding:24px}}'''

def page(config, demo=False):
    esc=html.escape
    web=(f'<a href="{esc(config.web_url,quote=True)}">Abrir MindeLine web</a>' if config.web_url else '<p>El enlace web aún no está configurado.</p>')
    apk=(f'<a class="secondary" href="{esc(config.apk_url,quote=True)}">Descargar APK de Android</a>' if config.apk_url else '<p class="note">La descarga de Android todavía no está disponible. Puedes continuar en la web.</p>')
    heading='Vista previa del acceso' if demo else 'Tu espacio MindeLine'
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MindeLine · Acceso</title><style>{STYLE}</style><main><small>MINDELINE</small><h1>{heading}</h1><p>Continúa desde tu navegador o desde la aplicación Android.</p>{web}{apk}<p class="note">Para una cuenta nueva, contacta al equipo: debe revisar y habilitar el acceso. Este prototipo no tiene formulario de registro automático ni transfiere las respuestas del bot.</p><p class="note">Si ya instalaste la app, Android puede abrirla directamente al tocar este enlace desde WhatsApp, una vez verificada la asociación del dominio.</p></main></html>'''


def bot_demo_page(config, step):
    esc=html.escape
    web_url=esc(config.demo_web_url,quote=True)
    def options(choices):
        return ''.join(f'<a class="{ "secondary" if index else "" }" href="/demo?step={esc(next_step,quote=True)}">{esc(label)}</a>'
                       for index,(label,next_step) in enumerate(choices))
    if step=='mood':
        conversation='''<div class="bubble user">Hola</div><div class="bubble bot">Hola 👋 Soy el bot de MindeLine. ¿Cómo te sientes hoy? Elige un emoji.
<small>Prototipo: no ingreses datos reales. MindeLine no guarda tus respuestas; WhatsApp/Meta procesa tus mensajes según sus condiciones. No es una evaluación clínica. Si estás en peligro inmediato, contacta los servicios de emergencia locales.</small>'''+options([('😄 Bien','medication'),('😐 Más o menos','medication'),('😟 Mal','medication')])+'</div>'
    elif step=='medication':
        conversation='''<div class="bubble user">Elegí un emoji</div><div class="bubble bot">1 de 3 · ¿Tomaste tu medicación como fue indicada?'''+options([('Sí','appointment'),('No','appointment'),('A veces','appointment')])+'</div>'
    elif step=='appointment':
        conversation='''<div class="bubble user">Respondí la pregunta 1</div><div class="bubble bot">2 de 3 · ¿Podrás asistir a tu próxima cita?'''+options([('Sí','nursing'),('No puedo asistir','nursing')])+'</div>'
    elif step=='nursing':
        conversation='''<div class="bubble user">Respondí la pregunta 2</div><div class="bubble bot">3 de 3 · ¿Quieres hablar con enfermería?'''+options([('Sí, por favor','destination'),('No, gracias','destination')])+'</div>'
    elif step=='destination':
        conversation='''<div class="bubble user">Respondí la pregunta 3</div><div class="bubble bot">Gracias. ¿Cómo quieres continuar?'''+options([('Abrir web','consent_web'),('Abrir app Android','consent_android')])+'</div>'
    elif step in {'consent_web','consent_android'}:
        destination='web' if step=='consent_web' else 'android'
        conversation='''<div class="bubble user">Quiero continuar</div><div class="bubble bot">Antes de continuar: en un servicio real, tus respuestas podrían conservarse y ser consultadas por profesionales de salud autorizados y asignados para atenderte.
<small>En este prototipo, aceptar solo simula tu decisión: no crea una cuenta ni guarda o comparte el chat. No es consentimiento informado ni una firma legal. Si aceptas, podrás solicitar acceso; el equipo debe habilitar la cuenta. Puedes rechazar sin continuar.</small>'''+options([('Acepto y continuar',destination),('No acepto','declined')])+'</div>'
    elif step=='declined':
        conversation='''<div class="bubble user">No acepto</div><div class="bubble bot">No se continuará con el registro. La simulación no guardó ni compartió tus respuestas. Gracias por participar.</div>'''
    elif step=='web':
        conversation=f'''<div class="bubble user">Acepto y continuar</div><div class="bubble bot">Abre MindeLine y contacta al equipo para solicitar acceso. Esta demo no crea cuentas automáticamente; el equipo debe revisar y habilitar cada cuenta.
<a href="{web_url}">Abrir MindeLine (demo local)</a><small>La simulación no guarda ni transfiere las respuestas del chat.</small></div>'''
    elif step=='android':
        conversation=f'''<div class="bubble user">Acepto y continuar</div><div class="bubble bot">La app Android todavía no está disponible en esta demostración. Para solicitar una cuenta nueva, contacta al equipo; debe revisar y habilitar cada acceso.
<a href="{web_url}">Continuar por la web</a><small>La simulación no guarda ni transfiere las respuestas del chat.</small></div>'''
    else:
        conversation='''<div class="bubble user">Hola</div><div class="bubble bot">Envía “Hola” para comenzar. Primero te preguntaré cómo te sientes hoy y luego haré tres preguntas breves.
<a href="/demo?step=mood">Enviar Hola</a></div>'''
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MindeLine · Bot de WhatsApp (demo)</title><style>{STYLE}
body{{background:#e9f1ed}}main{{max-width:480px;margin:5vh auto;padding:0;overflow:hidden}}header{{background:#075e54;color:white;padding:18px 22px;font-weight:700}}.chat{{padding:24px 18px;min-height:310px;background:#efeae2}}.bubble{{max-width:88%;padding:14px 16px;margin:12px 0;border-radius:14px;white-space:pre-line}}.user{{margin-left:auto;background:#d9fdd3}}.bot{{background:white}}.bubble small{{display:block;margin-top:10px}}.bubble a{{margin:12px 0 0;padding:12px 14px}}.bubble a.secondary{{background:#e4e9f1;color:#192436}}.foot{{padding:14px 18px;background:white;font-size:13px;color:#5b6475}}</style><main><header>WhatsApp · MindeLine (simulación)</header><section class="chat">{conversation}</section><div class="foot">Demostración local: no se envían mensajes por WhatsApp ni se contacta a Meta. Solo datos ficticios.</div></main></html>'''


def create_app(config=None, send=None):
    config=config or Config.from_env();config.validate()
    seen={};sessions={};lock=asyncio.Lock()
    async def meta_send(payload):
        async with httpx.AsyncClient(timeout=8.0,follow_redirects=False) as client:
            response=await client.post('https://graph.facebook.com/'+config.graph_version+'/'+config.phone_id+'/messages',
                headers={'Authorization':'Bearer '+config.access_token},json=payload)
            response.raise_for_status()
    sender=send or meta_send

    async def health(request):return JSONResponse({'status':'ok','mode':config.mode})
    async def landing(request):return HTMLResponse(page(config))
    async def demo(request):
        if not config.demo_web_url:
            return HTMLResponse(page(config,True))
        step=request.query_params.get('step','')
        if step not in {'mood','medication','appointment','nursing','destination',
                        'consent_web','consent_android','declined','web','android'}:
            step=''
        return HTMLResponse(bot_demo_page(config,step))
    async def assetlinks(request):
        if not config.certificate:return JSONResponse([],status_code=503)
        return JSONResponse([{'relation':['delegate_permission/common.handle_all_urls'],
                             'target':{'namespace':'android_app','package_name':PACKAGE,
                                       'sha256_cert_fingerprints':[config.certificate.upper()]}}])

    async def webhook(request):
        if config.mode!='live':return PlainTextResponse('Webhook disabled in preview mode',status_code=503)
        if request.method=='GET':
            q=request.query_params
            if q.get('hub.mode')=='subscribe' and hmac.compare_digest(q.get('hub.verify_token',''),config.verify_token):
                return PlainTextResponse(q.get('hub.challenge',''))
            return PlainTextResponse('Forbidden',status_code=403)
        body=b''
        async for chunk in request.stream():
            body+=chunk
            if len(body)>MAX_BODY:return Response(status_code=413)
        if not valid_signature(body,request.headers.get('x-hub-signature-256'),config.app_secret):
            return Response(status_code=401)
        try:
            payload=json.loads(body)
            messages=incoming_events(payload,config)
        except (ValueError,TypeError,AttributeError):return Response(status_code=400)
        # A single worker + lock prevents duplicate replies in this process. No phone/body logs.
        if len(messages)>20:return Response(status_code=413)
        async with lock:
            now=time.monotonic()
            for key in list(seen):
                if now-seen[key]>24*3600:seen.pop(key)
            for key,recipient,raw in messages:
                if key in seen:continue
                if len(seen)>=5000:return Response(status_code=503)
                outgoing=advance_flow(recipient,raw,config,sessions)
                try:await sender(outgoing)
                except Exception:
                    # Non-2xx invites provider retry; already confirmed sends stay deduplicated.
                    return Response(status_code=502)
                seen[key]=time.monotonic()
        return Response(status_code=200)

    app=Starlette(routes=[Route('/health',health),Route('/',landing),Route('/open',landing),Route('/demo',demo),
                         Route('/demo/',demo),
                         Route('/.well-known/assetlinks.json',assetlinks),Route('/webhook',webhook,methods=['GET','POST'])])
    async def headers(request,call_next):
        response=await call_next(request)
        response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"})
        return response
    app.add_middleware(BaseHTTPMiddleware,dispatch=headers)
    return app

app=create_app()
