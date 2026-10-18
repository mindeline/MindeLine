import sys,time,json,hmac,hashlib
from pathlib import Path
import pytest
from starlette.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from channels.server import Config,create_app,reply_payload,valid_signature,events
from channels.configure_android import configure

@pytest.fixture
def cfg():
    return Config(mode='live',web_url='https://web.example.com',gateway_url='https://access.example.com',
        verify_token='test-verify-token-32-characters-xx',app_secret='test-secret',access_token='fake',phone_id='123456',graph_version='v23.0')

def payload(choice=None,mid='wamid.test',message_type='interactive'):
    msg={'id':mid,'from':'56911111111','timestamp':str(int(time.time())),'type':'text','text':{'body':'hola'}}
    if message_type=='audio':
        msg.update(type='audio',audio={'id':'audio.fake'})
    elif choice and message_type=='interactive':
        msg.update(type='interactive',interactive={'button_reply':{'id':choice}})
    elif choice:
        msg.update(type='text',text={'body':choice})
    return {'object':'whatsapp_business_account','entry':[{'changes':[{'field':'messages','value':{'metadata':{'phone_number_id':'123456'},'messages':[msg]}}]}]}

def body_headers(p,c):
    body=json.dumps(p).encode()
    return body,{'x-hub-signature-256':'sha256='+hmac.new(c.app_secret.encode(),body,hashlib.sha256).hexdigest()}

def test_unsigned_webhook_is_rejected(cfg):
    c=TestClient(create_app(cfg));assert c.post('/webhook',json=payload()).status_code==401

def test_verification_token(cfg):
    c=TestClient(create_app(cfg))
    assert c.get('/webhook',params={'hub.mode':'subscribe','hub.verify_token':'wrong','hub.challenge':'123'}).status_code==403
    r=c.get('/webhook',params={'hub.mode':'subscribe','hub.verify_token':cfg.verify_token,'hub.challenge':'123'})
    assert r.status_code==200 and r.text=='123'

def test_menu_and_duplicate_detection(cfg):
    sent=[]
    async def send(p):sent.append(p)
    with TestClient(create_app(cfg,send)) as c:
        body,h=body_headers(payload(),cfg)
        assert c.post('/webhook',content=body,headers=h).status_code==200
        assert c.post('/webhook',content=body,headers=h).status_code==200
    assert len(sent)==1
    assert [b['reply']['id'] for b in sent[0]['interactive']['action']['buttons']]==[
        'mood_good','mood_ok','mood_bad']

def test_whatsapp_flow_mood_three_questions_then_web(cfg):
    sent=[]
    async def send(p):sent.append(p)
    choices=['hola','mood_bad','med_no','appointment_no','nursing_yes','web','consent_accept']
    with TestClient(create_app(cfg,send)) as c:
        for index,choice in enumerate(choices):
            b,h=body_headers(payload(choice,mid='wamid.flow.'+str(index)),cfg)
            assert c.post('/webhook',content=b,headers=h).status_code==200
    assert '¿Cómo te sientes hoy?' in sent[0]['interactive']['body']['text']
    assert '1 de 3' in sent[1]['interactive']['body']['text']
    assert '2 de 3' in sent[2]['interactive']['body']['text']
    assert '3 de 3' in sent[3]['interactive']['body']['text']
    assert [b['reply']['id'] for b in sent[4]['interactive']['action']['buttons']]==['web','android']
    assert 'Antes de continuar' in sent[5]['interactive']['body']['text']
    assert 'https://web.example.com' in sent[6]['text']['body']
    assert 'habilitar tu acceso' in sent[6]['text']['body']

def test_whatsapp_flow_android_destination(cfg):
    sent=[]
    async def send(p):sent.append(p)
    choices=['hola','😄','sí','sí','no','android','consent_accept']
    with TestClient(create_app(cfg,send)) as c:
        for index,choice in enumerate(choices):
            b,h=body_headers(payload(choice,mid='wamid.android.'+str(index)),cfg)
            assert c.post('/webhook',content=b,headers=h).status_code==200
    assert 'https://access.example.com/open' in sent[-1]['text']['body']

def test_whatsapp_flow_declining_consent_closes_without_link(cfg):
    sent=[]
    async def send(p):sent.append(p)
    choices=['hola','mood_bad','med_no','appointment_no','nursing_yes','web','consent_decline']
    with TestClient(create_app(cfg,send)) as c:
        for index,choice in enumerate(choices):
            b,h=body_headers(payload(choice,mid='wamid.decline.'+str(index)),cfg)
            assert c.post('/webhook',content=b,headers=h).status_code==200
    assert [button['reply']['id'] for button in sent[5]['interactive']['action']['buttons']]==[
        'consent_accept','consent_decline']
    assert 'no se continuará' in sent[6]['text']['body'].casefold()
    assert 'no guardó ni compartió' in sent[6]['text']['body'].casefold()
    assert all('https://web.example.com' not in message.get('text',{}).get('body','') for message in sent[6:])

def test_whatsapp_flow_consent_reminder_keeps_selected_destination(cfg):
    sent=[]
    async def send(p):sent.append(p)
    choices=['hola','mood_good','med_yes','appointment_yes','nursing_no','android','invalid','consent_accept']
    with TestClient(create_app(cfg,send)) as c:
        for index,choice in enumerate(choices):
            b,h=body_headers(payload(choice,mid='wamid.reminder.'+str(index)),cfg)
            assert c.post('/webhook',content=b,headers=h).status_code==200
    assert 'Elige una de las opciones' in sent[6]['interactive']['body']['text']
    assert 'https://access.example.com/open' in sent[7]['text']['body']

def test_whatsapp_flow_accepts_typed_answers_and_explains_audio(cfg):
    sent=[]
    async def send(p):sent.append(p)
    choices=['hola','😐 Más o menos','A veces','No puedo asistir','Sí, por favor','app','consent_accept']
    with TestClient(create_app(cfg,send)) as c:
        for index,choice in enumerate(choices):
            b,h=body_headers(payload(choice,mid='wamid.typed.'+str(index),message_type='text'),cfg)
            assert c.post('/webhook',content=b,headers=h).status_code==200
        b,h=body_headers(payload(mid='wamid.audio',message_type='audio'),cfg)
        assert c.post('/webhook',content=b,headers=h).status_code==200
    assert 'https://access.example.com/open' in sent[-2]['text']['body']
    assert 'No escucho ni guardo audios' in sent[-1]['text']['body']

@pytest.mark.parametrize('choice,expected',[('web','https://web.example.com'),('android','https://access.example.com/open')])
def test_menu_choices(cfg,choice,expected):
    assert expected in events(payload(choice),cfg)[0][1]['text']['body']

def test_wrong_account_and_stale_events_ignored(cfg):
    p=payload();p['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']='other'
    assert events(p,cfg)==[]
    p=payload();p['entry'][0]['changes'][0]['value']['messages'][0]['timestamp']='1'
    assert events(p,cfg)==[]

def test_delivery_failure_allows_retry(cfg):
    attempts=[]
    async def send(p):
        attempts.append(1)
        if len(attempts)==1:raise RuntimeError('no credentials shown')
    with TestClient(create_app(cfg,send)) as c:
        b,h=body_headers(payload(),cfg)
        assert c.post('/webhook',content=b,headers=h).status_code==502
        assert c.post('/webhook',content=b,headers=h).status_code==200
        assert len(attempts)==2

def test_preview_never_sends():
    with TestClient(create_app(Config())) as c:
        assert c.post('/webhook',json={}).status_code==503
        assert c.get('/demo').status_code==200
        assert 'todavía no está disponible' in c.get('/open').text
        assert c.get('/.well-known/assetlinks.json').status_code==503

def test_local_bot_demo_links_to_mindeline_without_whatsapp():
    config=Config(demo_web_url='http://127.0.0.1:8502')
    with TestClient(create_app(config)) as c:
        assert 'Enviar Hola' in c.get('/demo').text
        mood=c.get('/demo',params={'step':'mood'}).text
        assert '¿Cómo te sientes hoy?' in mood and '😄 Bien' in mood and '😟 Mal' in mood
        assert '¿Tomaste tu medicación' in c.get('/demo',params={'step':'medication'}).text
        assert '¿Podrás asistir a tu próxima cita?' in c.get('/demo',params={'step':'appointment'}).text
        assert '¿Quieres hablar con enfermería?' in c.get('/demo',params={'step':'nursing'}).text
        end=c.get('/demo',params={'step':'destination'}).text
        assert 'consent_web' in end and 'consent_android' in end
        consent=c.get('/demo',params={'step':'consent_web'}).text
        assert 'aceptar solo simula tu decisión' in consent
        assert 'declined' in consent and 'web' in consent
        web=c.get('/demo',params={'step':'web'}).text
        assert 'Abrir MindeLine (demo local)' in web
        assert 'no guarda ni transfiere' in web
        assert config.demo_web_url in web
        declined=c.get('/demo',params={'step':'declined'}).text
        assert 'no guardó ni compartió tus respuestas' in declined
        assert 'todavía no está disponible' in c.get('/demo',params={'step':'android'}).text
        assert c.post('/webhook',json={}).status_code==503

@pytest.mark.parametrize('url',[
    'https://mindeline.example','http://example.com:8502','http://127.0.0.1',
    'http://127.0.0.1:8502/?patient=1'])
def test_demo_web_url_only_allows_local_preview(url):
    with pytest.raises(ValueError):
        Config(demo_web_url=url).validate()

@pytest.mark.parametrize('value',['http://example.com','https://user:pw@example.com','https://example.com/?patient=123','https://example.invalid'])
def test_unsafe_config_rejected(value):
    with pytest.raises(ValueError):Config(web_url=value).validate()

def test_assetlinks_matches_mobile_package(cfg):
    from dataclasses import replace
    c=TestClient(create_app(replace(cfg,certificate=':'.join(['AA']*32))))
    r=c.get('/.well-known/assetlinks.json')
    assert r.status_code==200 and r.json()[0]['target']['package_name']=='app.mindeline.mobile'

def test_android_config_generator(tmp_path):
    import xml.etree.ElementTree as ET
    (tmp_path/'app/src/main/res/values').mkdir(parents=True)
    configure('https://web.example.com','https://access.example.com',tmp_path)
    assert 'gatewayHost=access.example.com' in (tmp_path/'mindeline.properties').read_text()
    root=ET.parse(tmp_path/'app/src/main/res/values/strings.xml').getroot()
    assert 'web.example.com' in root.find("string[@name='asset_statements']").text
