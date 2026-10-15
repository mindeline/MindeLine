import json
from groq import Groq


def procesar_audio_o_texto(api_key, texto_ingresado=None, audio_file_path=None, idioma="es"):
    client = Groq(api_key=api_key)
    
    transcripcion = ""
    if audio_file_path:
        with open(audio_file_path, "rb") as file:
            transcribe = client.audio.transcriptions.create(
                file=(audio_file_path, file.read()),
                model="whisper-large-v3",
                language=idioma
            )
            transcripcion = transcribe.text
    else:
        transcripcion = texto_ingresado

    if idioma == "en":
        prompt_sistema = """
        You are the triage engine for MindeLine, a mental health support platform.
        Assess the patient's message using these risk levels:
        - Level A (Emergency): Mentions death, active suicidal ideation or plan, recent attempt,
          dangerous medication ingestion, or severe life-threatening symptoms.
        - Level B (Urgent): Severe distress, agitation, intense suspiciousness, or same-day
          medical attention may be needed.
        - Level C (Priority): Worsening symptoms, significant pain or low mood; follow-up
          with the care team within 72 hours may be needed.
        - Level D (Follow-up): Mild changes or questions about treatment/adherence; notify
          the care team.
        - Level E (Routine): Stable status with no warning signs.

        Respond ONLY with strict JSON using these keys:
        {
          "nivel_riesgo": "A" | "B" | "C" | "D" | "E",
          "resumen_clinico": "Concise 1-2 sentence summary in English",
          "phq9_estimado": number from 0 to 27, or null if not applicable,
          "alerta_frase": "Exact patient phrase that triggered the alert"
        }
        """
        mensaje_usuario = f"Patient message: '{transcripcion}'"
    else:
        prompt_sistema = """
        Eres el motor de triaje de la plataforma de salud mental MindeLine.
        Evalúa el mensaje del paciente con estos niveles de riesgo:
        - Nivel A (Emergencia): Menciona muerte, ideación o plan suicida activo, intento reciente,
          ingesta peligrosa de medicamentos o síntomas vitales graves.
        - Nivel B (Urgente): Angustia severa, agitación, suspicacia intensa o posible necesidad
          de atención médica el mismo día.
        - Nivel C (Prioritario): Empeoramiento de síntomas, dolor o desánimo significativo;
          puede requerir seguimiento del equipo tratante en 72 horas.
        - Nivel D (Seguimiento): Cambios leves o dudas sobre tratamiento/adherencia; informar
          al equipo tratante.
        - Nivel E (Rutina): Estado estable sin señales de alerta.

        Responde ÚNICAMENTE con JSON estricto usando estas claves:
        {
          "nivel_riesgo": "A" | "B" | "C" | "D" | "E",
          "resumen_clinico": "Síntesis concisa en 1-2 oraciones en español",
          "phq9_estimado": número del 0 al 27, o null si no aplica,
          "alerta_frase": "Frase exacta del paciente que activó la alerta"
        }
        """
        mensaje_usuario = f"Mensaje del paciente: '{transcripcion}'"

    # Modelos activos en tu cuenta según el diagnóstico
    modelos_disponibles = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "allam-2-7b"]

    for mod in modelos_disponibles:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensaje_usuario}
                ],
                model=mod,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            respuesta_json = json.loads(chat_completion.choices[0].message.content)
            return transcripcion, respuesta_json
        except Exception:
            continue

    if idioma == "en":
        raise RuntimeError("Could not process the request with the available models.")
    raise RuntimeError("No se pudo procesar la solicitud con los modelos disponibles.")