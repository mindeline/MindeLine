import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

def obtener_cliente_groq(api_key=None):
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        logging.error("No se encontró GROQ_API_KEY en las variables de entorno.")
        raise ValueError("API Key de Groq no configurada.")
    return Groq(api_key=key)

def procesar_audio_o_texto(api_key=None, texto_ingresado=None, audio_file_path=None):
    client = obtener_cliente_groq(api_key)
    
    transcripcion = ""
    if audio_file_path:
        try:
            logging.info(f"Iniciando transcripción del audio: {audio_file_path}")
            with open(audio_file_path, "rb") as file:
                transcribe = client.audio.transcriptions.create(
                    file=(audio_file_path, file.read()),
                    model="whisper-large-v3",
                    language="es"
                )
                transcripcion = transcribe.text
                logging.info("Transcripción completada con éxito.")
        except Exception as e:
            logging.error(f"Error en Whisper STT: {e}")
            raise e
    else:
        transcripcion = texto_ingresado or ""

    prompt_sistema = """
    Eres el motor de triaje de la plataforma de salud mental MindeLine. 
    Tu trabajo es evaluar el mensaje transcrito de un paciente y aplicar las reglas clínicas:
    NIVELES DE RIESGO:
    - Nivel A (Emergencia): Habla de muerte, ideación/plan suicida activo, intento reciente, ingesta peligrosa de medicamentos, o síntomas vitales graves (SAMU 131 / *4141).
    - Nivel B (Urgente): Crisis severa de angustia, agitación, suspicacia intensa, necesidad de médico el mismo día.
    - Nivel C (Prioritario): Empeoramiento de síntomas, dolor o desánimo elevado, necesita hora con tratante en 72h.
    - Nivel D (Seguimiento): Cambios leves, dudas sobre tratamiento o adherencia, requiere nota al tratante.
    - Nivel E (Rutina): Estado estable, reporte habitual sin señales de alarma.

    Debes responder ÚNICAMENTE en formato JSON estricto con las siguientes claves:
    {
      "nivel_riesgo": "A" | "B" | "C" | "D" | "E",
      "resumen_clinico": "Sintesis concisa en 1-2 oraciones del estado reportado",
      "phq9_estimado": numero_del_0_al_27 (o null si no aplica),
      "alerta_frase": "Frase exacta del paciente que activó la alerta"
    }
    """

    modelos_disponibles = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "allam-2-7b"]

    for mod in modelos_disponibles:
        try:
            logging.info(f"Enviando solicitud de triaje a Groq con modelo: {mod}")
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Mensaje del paciente: '{transcripcion}'"}
                ],
                model=mod,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            respuesta_json = json.loads(chat_completion.choices[0].message.content)
            logging.info(f"Triaje exitoso con modelo {mod}. Nivel: {respuesta_json.get('nivel_riesgo')}")
            return transcripcion, respuesta_json
        except Exception as err:
            logging.warning(f"Fallo el modelo {mod}: {err}. Intentando con el siguiente...")
            continue

    logging.error("Todos los modelos de la lista fallaron en la inferencia.")
    raise RuntimeError("No se pudo obtener la clasificación del triaje.")

def responder_chatbot(api_key, historial_mensajes):
    """
    Recibe el historial de conversación en formato de lista de dicts
    y devuelve la respuesta empática del chatbot MindeBot.
    """
    client = obtener_cliente_groq(api_key)
    
    prompt_chatbot = """
    Eres MindeBot, el asistente virtual empático y seguro de la plataforma MindeLine.
    Tu objetivo es brindar contención emocional, escuchar activamente y orientar al usuario.
    
    Reglas de conducta:
    1. Sé empático, cálido, profesional y no juzgues.
    2. Aclara siempre de forma sutil que eres una IA de apoyo y no reemplazas una consulta médica/psicológica.
    3. Si detectas señales explícitas de ideación suicida o emergencia vital, proporciona inmediatamente las líneas de crisis en Chile:
       - Fono Salud Responde: *4141 (Prevención del Suicidio)
       - SAMU: 131
    4. Mantén respuestas concisas (máximo 2-3 párrafos breves) para no abrumar al usuario.
    """

    messages = [{"role": "system", "content": prompt_chatbot}] + historial_mensajes
    modelos_disponibles = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "allam-2-7b"]
    
    for mod in modelos_disponibles:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=mod,
                temperature=0.7,
                max_tokens=500
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logging.warning(f"Error en chatbot con modelo {mod}: {e}")
            continue

    return "Lo siento, en este momento no puedo procesar tu respuesta. Si te encuentras en una situación de emergencia, por favor llama al *4141 o al 131."

def responder_chatbot_guiado(api_key, opcion_seleccionada):
    """
    Recibe la opción de clic seleccionada por el usuario y genera 
    la respuesta empática + el siguiente set de preguntas/opciones.
    """
    client = obtener_cliente_groq(api_key)
    
    prompt_sistema = """
    Eres MindeBot, el asistente virtual empático de la plataforma MindeLine.
    El usuario interactúa haciendo clic en opciones predeterminadas.
    
    Debes responder ÚNICAMENTE en formato JSON estricto con la siguiente estructura:
    {
      "respuesta": "Mensaje empático, breve y de contención emocional (máximo 2 párrafos). Si hay riesgo de vida, incluye siempre el *4141 y SAMU 131.",
      "siguientes_opciones": [
        "Opción corta 1",
        "Opción corta 2",
        "Opción corta 3"
      ]
    }
    
    Genera siempre de 2 a 4 opciones de seguimiento relevantes para continuar la conversación de forma fluida.
    """

    modelos = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "allam-2-7b"]
    
    for mod in modelos:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"El paciente seleccionó la opción: '{opcion_seleccionada}'"}
                ],
                model=mod,
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            logging.warning(f"Error en chatbot guiado con {mod}: {e}")
            continue

    return {
        "respuesta": "Entiendo cómo te sientes. Recuerda que no estás solo/a y en MindeLine estamos para acompañarte. Si necesitas ayuda de emergencia, llama al *4141.",
        "siguientes_opciones": ["Quiero hablar con un profesional", "Ver ejercicios de respiración", "Volver al inicio"]
    }