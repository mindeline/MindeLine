import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, guardar_alerta, obtener_alertas, actualizar_estado_alerta
from backend_ai import procesar_audio_o_texto

TRANSLATIONS = {
    "Español": {},
    "English": {
        "🔐 Perfil de demostración": "🔐 Demo profile",
        "Ver la experiencia como": "View the experience as",
        "Paciente": "Patient",
        "Enfermería": "Nursing",
        "Equipo tratante": "Care team",
        "Selector de demo; no es inicio de sesión ni control de acceso.": "Demo selector; this is not a login or access control.",
        "Tu espacio de acompañamiento": "Your support space",
        "Comparte cómo te sientes mediante el simulador de mensajes. Si necesitas ayuda inmediata, contacta los servicios de emergencia locales o a tu equipo de salud.": "Share how you are feeling using the message simulator. If you need immediate help, contact local emergency services or your healthcare team.",
        "1. Compartir una actualización": "1. Share an update",
        "2. El equipo revisa la solicitud": "2. The team reviews the request",
        "3. Recibir seguimiento": "3. Receive follow-up",
        "Flujo de recepción y acompañamiento": "Intake and support workflow",
        "Revisa la bandeja, identifica solicitudes pendientes y marca cada caso cuando haya sido revisado.": "Review the inbox, identify pending requests, and mark each case once reviewed.",
        "1. Revisar casos entrantes": "1. Review incoming cases",
        "2. Tomar o marcar casos": "2. Take or mark cases",
        "3. Derivar al equipo tratante cuando corresponda": "3. Refer to the care team when appropriate",
        "Flujo de revisión clínica": "Clinical review workflow",
        "Consulta la ficha, revisa alertas y utiliza los filtros de apoyo como referencia; valida siempre las decisiones clínicamente.": "Review the patient record and alerts. Use support filters as references and always validate decisions clinically.",
        "1. Revisar ficha e historial": "1. Review the record and history",
        "2. Evaluar alertas priorizadas": "2. Assess prioritized alerts",
        "3. Registrar seguimiento en la ficha": "3. Record follow-up in the patient record",
        "Prototipo de demostración con datos sintéticos. No usar para decisiones clínicas ni datos reales.": "Demo prototype with synthetic data. Do not use for clinical decisions or real patient data.",
        "MindeLine: Ficha Clínica & Triaje Digital": "MindeLine: Clinical Record & Digital Triage",
        "Plataforma de Asistencia Clínica en Tiempo Real | Protocolos Algorítmicos A-E": "Real-Time Clinical Support Platform | A-E Triage Protocols",
        "Resumen ejecutivo": "Executive summary",
        "Panel clínico para priorización de riesgo, apoyo enfermero y coordinación del equipo tratante.": "Clinical dashboard for risk prioritization, nursing support, and care-team coordination.",
        "Trastornos mentales y del comportamiento": "Mental and behavioral disorders",
        "Trastornos del ánimo": "Mood disorders",
        "Depresión mayor": "Major depressive disorder",
        "Trastorno depresivo recurrente": "Recurrent depressive disorder",
        "Trastornos del ánimo persistentes": "Persistent mood disorders",
        "Trastornos neuróticos, relacionados con estrés y somatomorfos": "Neurotic, stress-related, and somatoform disorders",
        "Trastornos de ansiedad": "Anxiety disorders",
        "Reacciones ante estrés severo": "Reactions to severe stress",
        "Otros trastornos neuróticos": "Other neurotic disorders",
        "Síntomas, signos y hallazgos anormales": "Symptoms, signs, and abnormal findings",
        "Síntomas del sistema nervioso y del organismo": "Symptoms involving the nervous system and body",
        "Síntomas de ansiedad": "Symptoms of anxiety",
        "Síntomas y signos del sistema nervioso": "Symptoms and signs involving the nervous system",
        "Configuración del Sistema": "System settings",
        "Groq API Key": "Groq API key",
        "Selección de Paciente": "Patient selection",
        "Paciente para la prueba": "Patient for the demo",
        "➕ Agregar Nuevo Paciente": "➕ Add new patient",
        "Nombre y Apellido del Nuevo Paciente": "New patient's full name",
        "Juan Pérez": "Juan Perez",
        "Ficha del paciente": "Patient record",
        "Edad": "Age",
        "Género": "Gender",
        "Femenino": "Female",
        "Masculino": "Male",
        "No binario": "Non-binary",
        "Prefiero no decirlo": "Prefer not to say",
        "Antecedentes relevantes": "Relevant medical history",
        "Motivo de consulta": "Reason for visit",
        "Síntomas principales": "Main symptoms",
        "Tratamiento / medicación": "Treatment / medication",
        "Red de apoyo": "Support network",
        "Sí": "Yes",
        "No": "No",
        "Guardar ficha": "Save patient record",
        "Ahora": "Now",
        "✅ Ficha actualizada para {name}": "✅ Patient record updated for {name}",
        "Simulador de Mensajes": "Message simulator",
        "Canal de Entrada": "Input method",
        "Texto Directo": "Text message",
        "Nota de Voz (Audio)": "Voice note (audio)",
        "Mensaje del Paciente": "Patient message",
        "Siento mucha angustia y dolor en el pecho, necesito ayuda.": "I feel very anxious and have chest pain. I need help.",
        "Enviar Mensaje": "Send message",
        "Ingresa la API Key de Groq.": "Enter your Groq API key.",
        "Procesando con Llama 3...": "Processing with Llama 3...",
        "Texto": "Text",
        "✅ Alerta registrada para {name}": "✅ Alert recorded for {name}",
        "Subir nota de voz (.mp3, .wav)": "Upload a voice note (.mp3, .wav)",
        "Procesar Audio": "Process audio",
        "Transcribiendo con Whisper...": "Transcribing with Whisper...",
        "Audio": "Audio",
        "[Nota de voz]": "[Voice note]",
        "✅ Audio procesado para {name}": "✅ Audio processed for {name}",
        "NIVEL A - EMERGENCIA": "LEVEL A - EMERGENCY",
        "NIVEL B - URGENCIA": "LEVEL B - URGENT",
        "NIVEL C - PRIORITARIO": "LEVEL C - PRIORITY",
        "NIVEL D - SEGUIMIENTO": "LEVEL D - FOLLOW-UP",
        "NIVEL E - RUTINA": "LEVEL E - ROUTINE",
        "🚨 **PROTOCOLO DE CRISIS:** Derivar a SAMU 131 o Salud Responde *4141.": "🚨 **CRISIS PROTOCOL:** Contact local emergency services or the patient's care team immediately.",
        "Transcripción": "Transcript",
        "Síntesis": "Summary",
        "PHQ-9 estimado": "Estimated PHQ-9",
        "Tomar Caso": "Take case",
        "En Atencion": "In progress",
        "🏠 Dashboard": "🏠 Dashboard",
        "🧾 Ficha Clínica": "🧾 Patient record",
        "🚨 Triaje Clínico": "🚨 Clinical triage",
        "🏥 Enfermería": "🏥 Nursing",
        "👩‍⚕️ Equipo Tratante": "👩‍⚕️ Care team",
        "📈 Evolución": "📈 Trends",
        "Interacciones totales": "Total interactions",
        "Pendientes": "Pending",
        "Estado clínico actual": "Current clinical status",
        "Último caso: {name} · nivel {level} · {status} · {date}\n\n{summary}": "Latest case: {name} · level {level} · {status} · {date}\n\n{summary}",
        "No hay alertas registradas aún. El sistema está listo para recibir mensajes o audio del paciente.": "No alerts have been recorded yet. The system is ready to receive patient text or audio messages.",
        "Riesgo del paciente activo": "Active patient's risk",
        "Paciente: {name}": "Patient: {name}",
        "Edad: {age} años": "Age: {age} years",
        "Ficha clínica de {name}": "Clinical record for {name}",
        "Riesgo actual": "Current risk",
        "Última revisión": "Last review",
        "Sin antecedentes cargados.": "No medical history entered.",
        "Sin motivo registrado.": "No reason for visit recorded.",
        "Sin síntomas registrados.": "No symptoms recorded.",
        "Sin medicación cargada.": "No medication entered.",
        "Estado general": "Overall status",
        "Estable": "Stable",
        "Necesita seguimiento": "Follow-up needed",
        "### Resumen ejecutivo": "### Executive summary",
        "Paciente {name} ({age} años), con {reason}. Actualmente presenta {symptoms}. Se recomienda revisar nivel {level} y reforzar seguimiento si corresponde.": "Patient {name} ({age} years old) presents with {reason}. Current symptoms: {symptoms}. Review risk level {level} and provide follow-up as appropriate.",
        "👋 No hay alertas registradas.": "👋 No alerts have been recorded.",
        "Interacciones Totales": "Total interactions",
        "Emergencias Nivel A": "Level A emergencies",
        "Urgencias Nivel B": "Level B urgent cases",
        "Casos Pendientes": "Pending cases",
        "Bandeja de enfermería": "Nursing inbox",
        "Los casos recibidos por WhatsApp o por el simulador se revisan aquí antes de su derivación.": "Cases received through WhatsApp or the simulator are reviewed here before referral.",
        "Todavía no hay casos recibidos por WhatsApp.": "No WhatsApp cases have been received yet.",
        "alta": "High",
        "media": "Medium",
        "baja": "Low",
        "Alta": "High",
        "Media": "Medium",
        "Baja": "Low",
        "WhatsApp": "WhatsApp",
        "Teléfono": "Phone",
        "Resumen": "Summary",
        "Detalle": "Details",
        "Estado": "Status",
        "Urgencia {urgency}": "Urgency: {urgency}",
        "Marcar como revisado": "Mark as reviewed",
        "Revisado": "Reviewed",
        "### Casos registrados en MindeLine": "### Cases recorded in MindeLine",
        "Filtro de solicitudes médicas · CIE-10": "Medical request filter · ICD-10",
        "Prototipo de apoyo para equipo tratante. Datos de ejemplo y no reemplazan la validación clínica oficial.": "Decision-support prototype for the care team. Sample data only; it does not replace clinical review.",
        "Todos los grupos": "All groups",
        "Todas las categorías": "All categories",
        "Todas las subcategorías": "All subcategories",
        "1. Grupo / capítulo": "1. Group / chapter",
        "2. Categoría diagnóstica": "2. Diagnostic category",
        "3. Subcategoría específica": "3. Specific subcategory",
        "Se muestran {count} registros de ejemplo con un total de {total} casos. Estos recuentos no corresponden a un expediente clínico real.": "Showing {count} sample entries, with {total} cases in total. These counts do not represent real patient records.",
        "Sin resultados para este filtro. Intenta resetear o elegir otra combinación.": "No results for this filter. Reset or choose another combination.",
        "Seleccionar paciente para ver historial:": "Select a patient to view their history:",
        "fecha": "Date",
        "nivel": "Risk level",
        "resumen": "Summary",
        "estado": "Status",
        "cantidad": "Count",
        "Evolución por nivel de riesgo para {name}": "Risk-level trends for {name}",
        "No hay datos suficientes para graficar la evolución. Haz clic en el simulador para registrar una primera alerta.": "There is not enough data to display trends. Use the simulator to record the first alert.",
        "Pendiente": "Pending",
        "En Atención": "In progress",
        "Nivel": "Level",
        "Hoy": "Today",
        "Hace 2 días": "2 days ago",
        "Reciente": "Recent",
        "Nunca": "Never",
        "sin síntomas registrados": "no symptoms recorded",
        "consulta general": "general consultation",
        "NIVEL A - EMERGENCIA": "🔴 **LEVEL A - EMERGENCY**",
        "NIVEL B - URGENCIA": "🟠 **LEVEL B - URGENT**",
        "NIVEL C - PRIORITARIO": "🟡 **LEVEL C - PRIORITY**",
        "NIVEL D - SEGUIMIENTO": "🔵 **LEVEL D - FOLLOW-UP**",
        "NIVEL E - RUTINA": "🟢 **LEVEL E - ROUTINE**",
        "🏠 Dashboard": "🏠 Dashboard",
        "🧾 Ficha Clínica": "🧾 Patient record",
        "🚨 Triaje Clínico": "🚨 Clinical triage",
        "🏥 Enfermería": "🏥 Nursing",
        "👩‍⚕️ Equipo Tratante": "👩‍⚕️ Care team",
        "📈 Evolución": "📈 Trends",
        "🩺 Ficha del paciente": "🩺 Patient record",
        "📱 Simulador de Mensajes": "📱 Message simulator",
        "Código": "Code",
        "Nombre": "Name",
        "Casos": "Cases",
        "🧠 MindeLine: Ficha Clínica & Triaje Digital": "🧠 MindeLine: Clinical Record & Digital Triage",
        "Urgencia": "Urgency",
        "Group": "Group",
        "Category": "Category",
        "Code": "Code",
        "Name": "Name",
        "File change.": "File change.",
        "En Atencion": "In progress",
        "Sin medicación registrada.": "No medication recorded.",
        "No refiere medicación actual.": "Reports no current medication.",
        "PHQ-9 estimado": "Estimated PHQ-9",
        "Nivel A": "Level A",
        "Nivel B": "Level B",
        "Nivel actual": "Current level",
        "Grupo": "Group",
        "Categoría": "Category",
        "cantidad": "Count",
        "name": "Name",
        "fecha": "Date",
        "nivel": "Risk level",
        "resumen": "Summary",
        "estado": "Status",
        "Evolución por nivel de riesgo para {name}": "Risk-level trends for {name}",
        "Los casos recibidos por WhatsApp o por el simulador se revisan aquí antes de su derivación.": "Cases received through WhatsApp or the simulator are reviewed here before referral.",
        "Filtro de solicitudes médicas · CIE-10": "Medical request filter · ICD-10",
        "Prototipo de apoyo para equipo tratante. Datos de ejemplo y no reemplazan la validación clínica oficial.": "Decision-support prototype for the care team. Sample data only; it does not replace clinical review.",
        "📱 Simulador de Mensajes": "📱 Message simulator",
        "Sin antecedentes relevantes cargados.": "No relevant medical history entered.",
        "Consulta general.": "General consultation.",
        "Sin medicación registrada.": "No medication recorded.",
        "Sin síntomas registrados.": "No symptoms recorded.",
        "Ansiedad generalizada, antecedente de duelo reciente.": "Generalized anxiety; recent bereavement.",
        "Angustia intensa y sensación de presión torácica.": "Severe distress and a feeling of chest pressure.",
        "Palpitaciones, insomnio, llanto frecuente, baja energía.": "Palpitations, insomnia, frequent crying, and low energy.",
        "Sertralina 50 mg 1 vez/día.": "Sertraline 50 mg once daily.",
        "Hipertensión controlada.": "Controlled hypertension.",
        "Ansiedad y tensión durante la semana.": "Anxiety and increased tension this week.",
        "Nerviosismo, irritabilidad, dificultad para concentrarse.": "Nervousness, irritability, and difficulty concentrating.",
        "Paciente reporta ánimo muy bajo y ausencia de interés en actividades cotidianas.": "Patient reports very low mood and loss of interest in everyday activities.",
        "Ánimo: muy bajo • Medicación: No • Cita: No puedo asistir": "Mood: very low • Medication: No • Appointment: Unable to attend",
        "Consulta por ansiedad y aumento de tensión durante la semana.": "Reports anxiety and increased tension this week.",
        "Ánimo: regular • Medicación: Sí • Cita: Sí, agendada": "Mood: fair • Medication: Yes • Appointment: Scheduled",
        "Siento mucha angustia y dolor en el pecho, necesito ayuda.": "I feel very anxious and have chest pain. I need help.",
    },
}

CURRENT_LANGUAGE = "Español"


def tr(text, **values):
    translated = TRANSLATIONS.get(CURRENT_LANGUAGE, {}).get(text, text)
    return translated.format(**values) if values else translated


st.set_page_config(page_title="MindeLine", layout="wide", page_icon="🧠")
if "language" not in st.session_state:
    st.session_state.language = "Español"
CURRENT_LANGUAGE = st.sidebar.selectbox(
    "Language / Idioma",
    ["Español", "English"],
    index=["Español", "English"].index(st.session_state.language),
    key="language",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #f4fbff 0%, #eef5ff 35%, #f7f9fb 100%);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            color: #f8fafc;
        }

        [data-testid="stSidebar"] .st-emotion-cache-1y4p8pa,
        [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj,
        [data-testid="stSidebar"] .st-emotion-cache-16idsys {
            color: #e2e8f0;
        }

        .stTabs [role="tablist"] {
            background: rgba(255,255,255,0.7);
            border-radius: 14px;
            padding: 6px;
            gap: 8px;
        }

        .stTabs [role="tab"] {
            border-radius: 10px;
            padding: 0.7rem 1rem;
            font-weight: 600;
        }

        .stTabs [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            color: white;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.18);
        }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.8);
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 16px;
            padding: 0.8rem 1rem;
            box-shadow: 0 10px 20px rgba(15,23,42,0.04);
        }

        .stAlert {
            border-radius: 16px;
            border: 1px solid rgba(148,163,184,0.2);
            box-shadow: 0 12px 18px rgba(15,23,42,0.04);
        }

        .stExpander {
            background: rgba(255,255,255,0.68);
            border: 1px solid rgba(148,163,184,0.2);
            border-radius: 16px;
            padding: 0.2rem 0.5rem;
        }

        h1 {
            background: linear-gradient(135deg, #0f172a, #2563eb);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.04em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

if "demo_cases" not in st.session_state:
    st.session_state.demo_cases = [
        {
            "id": "WA-101",
            "nombre": "María González",
            "telefono": "+56 9 1111 2222",
            "canal": "WhatsApp",
            "urgencia": "alta",
            "estado": "Pendiente",
            "resumen": "Paciente reporta ánimo muy bajo y ausencia de interés en actividades cotidianas.",
            "detalle": "Ánimo: muy bajo • Medicación: No • Cita: No puedo asistir",
        },
        {
            "id": "WA-102",
            "nombre": "Carlos Muñoz",
            "telefono": "+56 9 3333 4444",
            "canal": "WhatsApp",
            "urgencia": "media",
            "estado": "Revisado",
            "resumen": "Consulta por ansiedad y aumento de tensión durante la semana.",
            "detalle": "Ánimo: regular • Medicación: Sí • Cita: Sí, agendada",
        },
    ]

CIE10_DATA = [
    {
        "id": "F",
        "nombre": "Trastornos mentales y del comportamiento",
        "categories": [
            {
                "id": "F30-F39",
                "nombre": "Trastornos del ánimo",
                "subcategories": [
                    {"code": "F32", "name": "Depresión mayor", "count": 132},
                    {"code": "F33", "name": "Trastorno depresivo recurrente", "count": 101},
                    {"code": "F34", "name": "Trastornos del ánimo persistentes", "count": 42},
                ],
            },
            {
                "id": "F40-F48",
                "nombre": "Trastornos neuróticos, relacionados con estrés y somatomorfos",
                "subcategories": [
                    {"code": "F41", "name": "Trastornos de ansiedad", "count": 188},
                    {"code": "F43", "name": "Reacciones ante estrés severo", "count": 57},
                    {"code": "F48", "name": "Otros trastornos neuróticos", "count": 26},
                ],
            },
        ],
    },
    {
        "id": "R",
        "nombre": "Síntomas, signos y hallazgos anormales",
        "categories": [
            {
                "id": "R40-R46",
                "nombre": "Síntomas del sistema nervioso y del organismo",
                "subcategories": [
                    {"code": "R45", "name": "Síntomas de ansiedad", "count": 74},
                    {"code": "R46", "name": "Síntomas y signos del sistema nervioso", "count": 33},
                ],
            }
        ],
    },
]

st.title(tr("🧠 MindeLine: Ficha Clínica & Triaje Digital"))
st.caption(tr("Plataforma de Asistencia Clínica en Tiempo Real | Protocolos Algorítmicos A-E"))

st.markdown(
    f"""
    <div style="margin: 0 0 1.2rem 0; padding: 1.2rem 1.4rem; border-radius: 18px; background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(14,165,233,0.12)); border: 1px solid rgba(59,130,246,0.15);">
        <div style="font-size: 0.8rem; letter-spacing: 0.12em; text-transform: uppercase; color: #2563eb; font-weight: 700;">{tr("Resumen ejecutivo")}</div>
        <div style="margin-top: 0.5rem; font-size: 1.05rem; color: #0f172a; font-weight: 600;">{tr("Panel clínico para priorización de riesgo, apoyo enfermero y coordinación del equipo tratante.")}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header(tr("🔐 Perfil de demostración"))
perfil_demo = st.sidebar.selectbox(
    tr("Ver la experiencia como"),
    ["Paciente", "Enfermería", "Equipo tratante"],
    format_func=tr,
)
st.sidebar.caption(tr("Selector de demo; no es inicio de sesión ni control de acceso."))

flujos_demo = {
    "Paciente": (
        "Tu espacio de acompañamiento",
        "Comparte cómo te sientes mediante el simulador de mensajes. Si necesitas ayuda inmediata, "
        "contacta los servicios de emergencia locales o a tu equipo de salud.",
        ["1. Compartir una actualización", "2. El equipo revisa la solicitud", "3. Recibir seguimiento"],
    ),
    "Enfermería": (
        "Flujo de recepción y acompañamiento",
        "Revisa la bandeja, identifica solicitudes pendientes y marca cada caso cuando haya sido revisado.",
        ["1. Revisar casos entrantes", "2. Tomar o marcar casos", "3. Derivar al equipo tratante cuando corresponda"],
    ),
    "Equipo tratante": (
        "Flujo de revisión clínica",
        "Consulta la ficha, revisa alertas y utiliza los filtros de apoyo como referencia; valida siempre las decisiones clínicamente.",
        ["1. Revisar ficha e historial", "2. Evaluar alertas priorizadas", "3. Registrar seguimiento en la ficha"],
    ),
}
titulo_flujo, descripcion_flujo, pasos_flujo = flujos_demo[perfil_demo]
st.markdown(f"### {tr(titulo_flujo)}")
st.caption(tr(descripcion_flujo))
pasos_cols = st.columns(len(pasos_flujo))
for columna, paso in zip(pasos_cols, pasos_flujo):
    columna.markdown(
        f"<div style='height:100%;padding:0.9rem 1rem;border:1px solid rgba(148,163,184,.25);"
        f"border-radius:14px;background:rgba(255,255,255,.72);font-weight:600'>{tr(paso)}</div>",
        unsafe_allow_html=True,
    )
st.caption(tr("Prototipo de demostración con datos sintéticos. No usar para decisiones clínicas ni datos reales."))

if "pacientes" not in st.session_state:
    st.session_state.pacientes = {
        "María González": {
            "edad": 32,
            "genero": "Femenino",
            "antecedentes": "Ansiedad generalizada, antecedente de duelo reciente.",
            "motivo": "Angustia intensa y sensación de presión torácica.",
            "sintomas": "Palpitaciones, insomnio, llanto frecuente, baja energía.",
            "tratamiento": "Sertralina 50 mg 1 vez/día.",
            "red_apoyo": "Sí",
            "ultima_revision": "Hoy",
            "riesgo": "B",
        },
        "Carlos Muñoz": {
            "edad": 41,
            "genero": "Masculino",
            "antecedentes": "Hipertensión controlada.",
            "motivo": "Ansiedad y tensión durante la semana.",
            "sintomas": "Nerviosismo, irritabilidad, dificultad para concentrarse.",
            "tratamiento": "No refiere medicación actual.",
            "red_apoyo": "Sí",
            "ultima_revision": "Hace 2 días",
            "riesgo": "C",
        },
    }


def perfil_base(nombre):
    base = {
        "edad": 30,
        "genero": "Femenino",
        "antecedentes": "Sin antecedentes relevantes cargados.",
        "motivo": "Consulta general.",
        "sintomas": "Sin síntomas registrados.",
        "tratamiento": "Sin medicación registrada.",
        "red_apoyo": "Sí",
        "ultima_revision": "Nunca",
        "riesgo": "E",
    }
    return st.session_state.pacientes.get(nombre, base)


st.sidebar.header(tr("⚙️ Configuración del Sistema"))
groq_key = st.sidebar.text_input(tr("Groq API Key"), type="password", value="")

st.sidebar.markdown("---")
st.sidebar.header(tr("👤 Selección de Paciente"))
opciones_pacientes = ["María González", "Carlos Muñoz", "Ana Silva", "Pedro Morales", "➕ Agregar Nuevo Paciente"]
paciente_seleccionado = st.sidebar.selectbox(
    tr("Paciente para la prueba"), opciones_pacientes, format_func=tr
)

if paciente_seleccionado == "➕ Agregar Nuevo Paciente":
    nombre_paciente = st.sidebar.text_input(
        tr("Nombre y Apellido del Nuevo Paciente"), tr("Juan Pérez")
    )
else:
    nombre_paciente = paciente_seleccionado

if nombre_paciente not in st.session_state.pacientes:
    st.session_state.pacientes[nombre_paciente] = perfil_base(nombre_paciente)

st.sidebar.markdown("---")
st.sidebar.header(tr("🩺 Ficha del paciente"))
with st.sidebar.form("form_ficha_paciente"):
    edad = st.number_input(tr("Edad"), min_value=0, max_value=120, value=int(st.session_state.pacientes[nombre_paciente].get("edad", 30)))
    generos = ["Femenino", "Masculino", "No binario", "Prefiero no decirlo"]
    genero_actual = st.session_state.pacientes[nombre_paciente].get("genero", "Femenino")
    genero = st.selectbox(tr("Género"), generos, index=generos.index(genero_actual), format_func=tr)
    antecedentes = st.text_area(tr("Antecedentes relevantes"), value=tr(st.session_state.pacientes[nombre_paciente].get("antecedentes", "")))
    motivo = st.text_area(tr("Motivo de consulta"), value=tr(st.session_state.pacientes[nombre_paciente].get("motivo", "")))
    sintomas = st.text_area(tr("Síntomas principales"), value=tr(st.session_state.pacientes[nombre_paciente].get("sintomas", "")))
    tratamiento = st.text_area(tr("Tratamiento / medicación"), value=tr(st.session_state.pacientes[nombre_paciente].get("tratamiento", "")))
    opciones_red = ["Sí", "No"]
    red_actual = st.session_state.pacientes[nombre_paciente].get("red_apoyo", "Sí")
    red_apoyo = st.radio(tr("Red de apoyo"), opciones_red, index=opciones_red.index(red_actual), format_func=tr)
    guardar_ficha = st.form_submit_button(tr("Guardar ficha"))

if guardar_ficha:
    st.session_state.pacientes[nombre_paciente] = {
        "edad": edad,
        "genero": genero,
        "antecedentes": antecedentes,
        "motivo": motivo,
        "sintomas": sintomas,
        "tratamiento": tratamiento,
        "red_apoyo": red_apoyo,
        "ultima_revision": "Ahora",
        "riesgo": st.session_state.pacientes[nombre_paciente].get("riesgo", "E"),
    }
    st.sidebar.success(tr("✅ Ficha actualizada para {name}", name=nombre_paciente))

st.sidebar.markdown("---")
st.sidebar.header(tr("📱 Simulador de Mensajes"))
canales_ingreso = ["Texto Directo", "Nota de Voz (Audio)"]
opcion_ingreso = st.sidebar.radio(tr("Canal de Entrada"), canales_ingreso, format_func=tr)

if opcion_ingreso == "Texto Directo":
    texto_simulado = st.sidebar.text_area(
        tr("Mensaje del Paciente"),
        tr("Siento mucha angustia y dolor en el pecho, necesito ayuda."),
    )
    if st.sidebar.button(tr("Enviar Mensaje"), use_container_width=True):
        if not groq_key:
            st.sidebar.error(tr("Ingresa la API Key de Groq."))
        else:
            with st.spinner(tr("Procesando con Llama 3...")):
                trans, json_res = procesar_audio_o_texto(
                    groq_key, texto_ingresado=texto_simulado,
                    idioma="en" if CURRENT_LANGUAGE == "English" else "es",
                )
                guardar_alerta(
                    nombre_paciente=nombre_paciente,
                    tipo_mensaje="Texto",
                    contenido=texto_simulado,
                    transcripcion=trans,
                    nivel=json_res["nivel_riesgo"],
                    resumen=json_res["resumen_clinico"],
                    phq9=json_res.get("phq9_estimado", 0),
                )
                st.session_state.pacientes[nombre_paciente]["riesgo"] = json_res["nivel_riesgo"]
                st.session_state.pacientes[nombre_paciente]["ultima_revision"] = "Reciente"
                st.sidebar.success(tr("✅ Alerta registrada para {name}", name=nombre_paciente))
                st.rerun()

elif opcion_ingreso == "Nota de Voz (Audio)":
    audio_file = st.sidebar.file_uploader(tr("Subir nota de voz (.mp3, .wav)"), type=["mp3", "wav", "m4a"])
    if audio_file and st.sidebar.button(tr("Procesar Audio"), use_container_width=True):
        if not groq_key:
            st.sidebar.error(tr("Ingresa la API Key de Groq."))
        else:
            with st.spinner(tr("Transcribiendo con Whisper...")):
                temp_path = f"temp_{audio_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(audio_file.getbuffer())

                trans, json_res = procesar_audio_o_texto(
                    groq_key, audio_file_path=temp_path,
                    idioma="en" if CURRENT_LANGUAGE == "English" else "es",
                )
                guardar_alerta(
                    nombre_paciente=nombre_paciente,
                    tipo_mensaje="Audio",
                    contenido="[Nota de voz]",
                    transcripcion=trans,
                    nivel=json_res["nivel_riesgo"],
                    resumen=json_res["resumen_clinico"],
                    phq9=json_res.get("phq9_estimado", 0),
                )
                st.session_state.pacientes[nombre_paciente]["riesgo"] = json_res["nivel_riesgo"]
                st.session_state.pacientes[nombre_paciente]["ultima_revision"] = "Reciente"
                st.sidebar.success(tr("✅ Audio procesado para {name}", name=nombre_paciente))
                st.rerun()


def mostrar_tarjeta_alerta(alerta):
    alerta_id, nombre, fecha, tipo, transcripcion, nivel, resumen, phq9, estado = alerta
    color_map = {
        "A": tr("NIVEL A - EMERGENCIA"),
        "B": tr("NIVEL B - URGENCIA"),
        "C": tr("NIVEL C - PRIORITARIO"),
        "D": tr("NIVEL D - SEGUIMIENTO"),
        "E": tr("NIVEL E - RUTINA"),
    }
    with st.expander(f"{color_map.get(nivel, nivel)} | {tr('Paciente: {name}', name=nombre)} | [{tr(estado)}] — {fecha}"):
        if nivel == "A":
            st.error(tr("🚨 **PROTOCOLO DE CRISIS:** Derivar a SAMU 131 o Salud Responde *4141."))
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{tr('Transcripción')}:** *\"{transcripcion}\"*")
            st.write(f"**{tr('Síntesis')}:** {resumen}")
            st.write(f"**{tr('PHQ-9 estimado')}:** {phq9}")
        with c2:
            if estado == "Pendiente":
                if st.button(tr("Tomar Caso"), key=f"btn_{alerta_id}"):
                    actualizar_estado_alerta(alerta_id, "En Atencion")
                    st.rerun()


tab_dashboard, tab_ficha, tab_triaje, tab_enfermeria, tab_tratante, tab_analitica = st.tabs(
    [
        tr("🏠 Dashboard"),
        tr("🧾 Ficha Clínica"),
        tr("🚨 Triaje Clínico"),
        tr("🏥 Enfermería"),
        tr("👩‍⚕️ Equipo Tratante"),
        tr("📈 Evolución"),
    ]
)

alertas = obtener_alertas()

perfil_actual = st.session_state.pacientes.get(nombre_paciente, perfil_base(nombre_paciente))

with tab_dashboard:
    total_alertas = len(alertas)
    urgencias_a = sum(1 for a in alertas if a[5] == "A")
    urgencias_b = sum(1 for a in alertas if a[5] == "B")
    pendientes = sum(1 for a in alertas if a[8] == "Pendiente")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric(tr("Interacciones totales"), total_alertas)
    d2.metric(tr("Nivel A"), urgencias_a)
    d3.metric(tr("Nivel B"), urgencias_b)
    d4.metric(tr("Pendientes"), pendientes)

    st.markdown("---")
    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"### {tr('Estado clínico actual')}")
        if alertas:
            ult = alertas[0]
            _, nombre_ult, fecha_ult, _, _, nivel_ult, resumen_ult, _, estado_ult = ult
            st.info(tr(
                "Último caso: {name} · nivel {level} · {status} · {date}\n\n{summary}",
                name=nombre_ult, level=nivel_ult, status=tr(estado_ult),
                date=fecha_ult, summary=resumen_ult,
            ))
        else:
            st.info(tr("No hay alertas registradas aún. El sistema está listo para recibir mensajes o audio del paciente."))
    with right:
        st.markdown(f"### {tr('Riesgo del paciente activo')}")
        riesgo_actual = perfil_actual.get("riesgo", "E")
        color_riesgo = {
            "A": "#dc2626",
            "B": "#f59e0b",
            "C": "#facc15",
            "D": "#3b82f6",
            "E": "#22c55e",
        }.get(riesgo_actual, "#94a3b8")
        st.markdown(
            f"<div style='padding: 1rem 1.1rem; border-radius: 16px; background: {color_riesgo}22; border: 1px solid {color_riesgo}; color: #0f172a; font-weight: 700; text-align: center;'>{tr('Nivel')} {riesgo_actual}</div>",
            unsafe_allow_html=True,
        )
        st.write(tr("Paciente: {name}", name=nombre_paciente))
        st.write(tr("Edad: {age} años", age=perfil_actual.get("edad", 0)))
        st.write(f"{tr('Red de apoyo')}: {tr(perfil_actual.get('red_apoyo', 'No'))}")

with tab_ficha:
    st.subheader(tr("Ficha clínica de {name}", name=nombre_paciente))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("Edad"), tr("Edad: {age} años", age=perfil_actual.get("edad", 0)))
    c2.metric(tr("Género"), tr(perfil_actual.get("genero", "-"))[:14])
    c3.metric(tr("Riesgo actual"), perfil_actual.get("riesgo", "E"))
    c4.metric(tr("Última revisión"), tr(perfil_actual.get("ultima_revision", "Nunca")))

    st.markdown("---")
    info1, info2 = st.columns(2)
    with info1:
        st.write(f"**{tr('Antecedentes relevantes')}:** {tr(perfil_actual.get('antecedentes', 'Sin antecedentes cargados.'))}")
        st.write(f"**{tr('Motivo de consulta')}:** {tr(perfil_actual.get('motivo', 'Sin motivo registrado.'))}")
        st.write(f"**{tr('Síntomas principales')}:** {tr(perfil_actual.get('sintomas', 'Sin síntomas registrados.'))}")
    with info2:
        st.write(f"**{tr('Tratamiento / medicación')}:** {tr(perfil_actual.get('tratamiento', 'Sin medicación cargada.'))}")
        st.write(f"**{tr('Red de apoyo')}:** {tr(perfil_actual.get('red_apoyo', 'No'))}")
        estado_general = "Estable" if perfil_actual.get("riesgo", "E") in ["D", "E"] else "Necesita seguimiento"
        st.write(f"**{tr('Estado general')}:** {tr(estado_general)}")

    st.markdown(f"### {tr('Resumen ejecutivo')}")
    motivo_resumen = tr(perfil_actual.get("motivo", "consulta general")).rstrip(". ")
    sintomas_resumen = tr(perfil_actual.get("sintomas", "sin síntomas registrados")).rstrip(". ")
    resumen_texto = tr(
        "Paciente {name} ({age} años), con {reason}. Actualmente presenta {symptoms}. Se recomienda revisar nivel {level} y reforzar seguimiento si corresponde.",
        name=nombre_paciente, age=perfil_actual.get("edad", 0),
        reason=motivo_resumen,
        symptoms=sintomas_resumen,
        level=perfil_actual.get("riesgo", "E"),
    )
    st.info(resumen_texto)

with tab_triaje:
    if not alertas:
        st.info(tr("👋 No hay alertas registradas."))
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(tr("Interacciones Totales"), len(alertas))
        m2.metric(tr("Emergencias Nivel A"), sum(1 for a in alertas if a[5] == "A"))
        m3.metric(tr("Urgencias Nivel B"), sum(1 for a in alertas if a[5] == "B"))
        m4.metric(tr("Casos Pendientes"), sum(1 for a in alertas if a[8] == "Pendiente"))
        st.markdown("---")
        for alerta in alertas:
            mostrar_tarjeta_alerta(alerta)

with tab_enfermeria:
    st.subheader(tr("Bandeja de enfermería"))
    st.caption(tr("Los casos recibidos por WhatsApp o por el simulador se revisan aquí antes de su derivación."))

    if not alertas and not st.session_state.demo_cases:
        st.info(tr("Todavía no hay casos recibidos por WhatsApp."))
    else:
        for caso in st.session_state.demo_cases:
            urgencia_label = {"alta": "Alta", "media": "Media", "baja": "Baja"}.get(caso["urgencia"], "Media")
            with st.container():
                st.markdown(f"### {caso['nombre']} · {caso['canal']}")
                st.write(f"**{tr('Teléfono')}:** {caso['telefono']}")
                st.write(f"**{tr('Resumen')}:** {tr(caso['resumen'])}")
                st.write(f"**{tr('Detalle')}:** {tr(caso['detalle'])}")
                st.write(f"**{tr('Estado')}:** {tr(caso['estado'])}")
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.badge(tr("Urgencia {urgency}", urgency=tr(urgencia_label)), icon="🚨")
                with col2:
                    if st.button(tr("Marcar como revisado"), key=f"demo_{caso['id']}"):
                        caso["estado"] = "Revisado"
                        st.rerun()
                st.markdown("---")

        if alertas:
            st.markdown(tr("### Casos registrados en MindeLine"))
            for alerta in alertas[:5]:
                alerta_id, nombre, fecha, tipo, transcripcion, nivel, resumen, phq9, estado = alerta
                st.write(f"- {nombre} | {tr('Nivel')} {nivel} | {tr(estado)} | {fecha}")

with tab_tratante:
    st.subheader(tr("Filtro de solicitudes médicas · CIE-10"))
    st.caption(tr("Prototipo de apoyo para equipo tratante. Datos de ejemplo y no reemplazan la validación clínica oficial."))

    grupos = ["Todos los grupos"] + [g["nombre"] for g in CIE10_DATA]
    grupo_sel = st.selectbox(tr("1. Grupo / capítulo"), grupos, format_func=tr)

    categorias = ["Todas las categorías"]
    if grupo_sel != "Todos los grupos":
        grupo_obj = next(g for g in CIE10_DATA if g["nombre"] == grupo_sel)
        categorias += [c["nombre"] for c in grupo_obj["categories"]]
    categoria_sel = st.selectbox(tr("2. Categoría diagnóstica"), categorias, format_func=tr)

    subcategorias = ["Todas las subcategorías"]
    if grupo_sel != "Todos los grupos":
        grupo_obj = next(g for g in CIE10_DATA if g["nombre"] == grupo_sel)
        if categoria_sel != "Todas las categorías":
            categoria_obj = next(c for c in grupo_obj["categories"] if c["nombre"] == categoria_sel)
            subcategorias += [s["name"] for s in categoria_obj["subcategories"]]
        elif categoria_sel == "Todas las categorías":
            for cat in grupo_obj["categories"]:
                subcategorias += [s["name"] for s in cat["subcategories"]]
    subcategoria_sel = st.selectbox(tr("3. Subcategoría específica"), subcategorias, format_func=tr)

    def obtener_entradas_filtradas():
        entradas = []
        for grupo in CIE10_DATA:
            for categoria in grupo["categories"]:
                for subcategoria in categoria["subcategories"]:
                    include = True
                    if grupo_sel != "Todos los grupos" and grupo["nombre"] != grupo_sel:
                        include = False
                    if include and categoria_sel != "Todas las categorías" and categoria["nombre"] != categoria_sel:
                        include = False
                    if include and subcategoria_sel != "Todas las subcategorías" and subcategoria["name"] != subcategoria_sel:
                        include = False
                    if include:
                        entradas.append({
                            "code": subcategoria["code"],
                            "name": subcategoria["name"],
                            "count": subcategoria["count"],
                            "grupo": grupo["nombre"],
                            "categoria": categoria["nombre"],
                        })
        return entradas

    resultados = obtener_entradas_filtradas()
    total = sum(r["count"] for r in resultados)
    if resultados:
        st.info(tr(
            "Se muestran {count} registros de ejemplo con un total de {total} casos. Estos recuentos no corresponden a un expediente clínico real.",
            count=len(resultados), total=total,
        ))
        if CURRENT_LANGUAGE == "English":
            nombres_columnas = {
                "code": "Code",
                "name": "Name",
                "count": "Cases",
                "grupo": "Group",
                "categoria": "Category",
            }
        else:
            nombres_columnas = {
                "code": "Código",
                "name": "Nombre",
                "count": "Casos",
                "grupo": "Grupo",
                "categoria": "Categoría",
            }
        dataframe_resultados = pd.DataFrame(resultados).rename(columns=nombres_columnas)
        if CURRENT_LANGUAGE == "English":
            dataframe_resultados["Name"] = dataframe_resultados["Name"].map(tr)
            dataframe_resultados["Group"] = dataframe_resultados["Group"].map(tr)
            dataframe_resultados["Category"] = dataframe_resultados["Category"].map(tr)
        st.dataframe(dataframe_resultados, use_container_width=True)
    else:
        st.warning(tr("Sin resultados para este filtro. Intenta resetear o elegir otra combinación."))

with tab_analitica:
    if alertas:
        df = pd.DataFrame(alertas, columns=["id", "nombre", "fecha", "tipo", "transcripcion", "nivel", "resumen", "phq9", "estado"])
        df["nivel"] = df["nivel"].fillna("E")
        pacientes_unicos = df["nombre"].unique().tolist()
        paciente_filtro = st.selectbox(tr("Seleccionar paciente para ver historial:"), pacientes_unicos)
        df_paciente = df[df["nombre"] == paciente_filtro]
        df_vista = df_paciente[["fecha", "nivel", "resumen", "estado"]].rename(
            columns={
                "fecha": tr("fecha"),
                "nivel": tr("nivel"),
                "resumen": tr("resumen"),
                "estado": tr("estado"),
            }
        )
        if CURRENT_LANGUAGE == "English":
            df_vista[tr("estado")] = df_vista[tr("estado")].map(tr)
        st.dataframe(df_vista, use_container_width=True)

        fig = px.bar(
            df_paciente.groupby("nivel").size().reset_index(name="cantidad"),
            x="nivel",
            y="cantidad",
            color="nivel",
            title=tr("Evolución por nivel de riesgo para {name}", name=paciente_filtro),
        )
        fig.update_layout(
            xaxis_title=tr("nivel"),
            yaxis_title=tr("cantidad"),
            legend_title_text=tr("nivel"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(tr("No hay datos suficientes para graficar la evolución. Haz clic en el simulador para registrar una primera alerta."))