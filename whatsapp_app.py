import os
import requests
import logging
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

from backend_ai import procesar_audio_o_texto
from db import guardar_alerta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

app = FastAPI(title="MindeLine - WhatsApp Webhook API")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@app.get("/")
def home():
    """
    Endpoint de comprobación para verificar que la API está activa.
    """
    return {"status": "ok", "message": "Servidor MindeLine WhatsApp API funcionando correctamente"}

@app.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(None),
    MediaUrl0: str = Form(None),
    NumMedia: int = Form(0)
):
    """
    Endpoint Webhook que recibe las notificaciones de mensajes desde Twilio WhatsApp.
    """
    response = MessagingResponse()
    msg = response.message()
    
    # Formatear el número telefónico del paciente (ej: 'whatsapp:+56912345678' -> '+56912345678')
    telefono_paciente = From.replace("whatsapp:", "").strip()
    nombre_paciente = f"Paciente ({telefono_paciente})"

    try:
        # 1. Caso: El paciente envió una Nota de Voz (Audio)
        if NumMedia > 0 and MediaUrl0:
            logging.info(f"Recibida nota de voz desde WhatsApp de: {telefono_paciente}")
            local_filename = "temp_whatsapp_audio.ogg"
            
            # Descargar el archivo de audio usando autenticación de Twilio
            auth_tuple = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None
            audio_req = requests.get(MediaUrl0, auth=auth_tuple)
            
            with open(local_filename, "wb") as f:
                f.write(audio_req.content)

            # Procesar transcripción STT + Triaje IA
            transcripcion, json_res = procesar_audio_o_texto(
                api_key=GROQ_API_KEY, 
                audio_file_path=local_filename
            )
            tipo_mensaje = "Audio WhatsApp"
            
            # Eliminar archivo de audio temporal
            if os.path.exists(local_filename):
                os.remove(local_filename)

        # 2. Caso: El paciente envió un Mensaje de Texto
        else:
            logging.info(f"Recibido texto desde WhatsApp de: {telefono_paciente}")
            transcripcion, json_res = procesar_audio_o_texto(
                api_key=GROQ_API_KEY, 
                texto_ingresado=Body or ""
            )
            tipo_mensaje = "Texto WhatsApp"

        # Extraer variables del JSON devuelto por el modelo
        nivel = json_res.get("nivel_riesgo", "E")
        resumen = json_res.get("resumen_clinico", "Sin resumen")
        phq9 = json_res.get("phq9_estimado", 0)

        # 3. Guardar la alerta en la base de datos compartida
        guardar_alerta(
            nombre_paciente=nombre_paciente,
            tipo_mensaje=tipo_mensaje,
            contenido=Body or "[Nota de Voz]",
            transcripcion=transcripcion,
            nivel=nivel,
            resumen=resumen,
            phq9=phq9
        )

        # 4. Respuesta automática según nivel de riesgo (Protocolo MindeLine)
        if nivel in ["A", "B"]:
            texto_respuesta = (
                f"🚨 *MindeLine - Alerta de Atención*\n\n"
                f"Hemos registrado tu mensaje. Tu equipo tratante ha sido notificado con urgencia.\n\n"
                f"⚠️ *Importante:* Si te encuentras en peligro o crisis agudo, por favor contacta a:\n"
                f"• Prevención del Suicidio: ***4141**\n"
                f"• SAMU: **131**\n\n"
                f"Puedes ingresar a tu portal de acompañamiento aquí:\n👉 https://mindeline.com"
            )
        else:
            texto_respuesta = (
                f"🧠 *MindeLine - Seguimiento Registrado*\n\n"
                f"Gracias por actualizar tu estado. He guardado tu información para la revisión de tu profesional de salud.\n\n"
                f"Si deseas realizar un ejercicio de orientación con MindeBot o ver tus indicaciones, ingresa a la web:\n"
                f"👉 https://mindeline.com"
            )

        msg.body(texto_respuesta)

    except Exception as e:
        logging.error(f"Error procesando mensaje de WhatsApp: {e}")
        msg.body("Hubo un inconveniente al registrar tu mensaje. Si te encuentras en una situación de emergencia, por favor llama al *4141 o al 131.")

    return Response(content=str(response), media_type="application/xml")