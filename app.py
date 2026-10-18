"""MindeLine · Ficha clínica y triaje digital (prototipo de demostración).

Interfaz Streamlit con la guía de diseño MindeLine v1.0 (octubre 2026).
Datos sintéticos: no usar con datos clínicos reales.
"""

import os
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import streamlit as st

from backend_ai import procesar_audio_o_texto
from db import actualizar_estado_alerta, guardar_alerta, init_db, obtener_alertas

# ---------------------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------------------

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS / "mindeline_logo_transparent.png"
# Si existe una versión blanca del logo (sobre navy), se usa en la barra lateral.
LOGO_SIDEBAR = next(
    (p for p in (ASSETS / "mindeline_logo_white.png", LOGO_PATH) if p.exists()), LOGO_PATH
)

st.set_page_config(
    page_title="MindeLine",
    layout="wide",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
)

LANGS = ["Español", "English"]
if "language" not in st.session_state:
    st.session_state.language = "Español"


def L(es, en):
    """Texto de interfaz según el idioma elegido."""
    return en if st.session_state.get("language") == "English" else es


# ---------------------------------------------------------------------------
# Guía de diseño: tokens y estilos
# ---------------------------------------------------------------------------

# Niveles de triaje → estados clínicos de la guía.
# clase CSS, etiqueta ES, etiqueta EN, color sólido (barra, punto, gráficos)
NIVELES = {
    "A": ("risk", "Emergencia", "Emergency", "#D64545"),
    "B": ("review", "Urgencia", "Urgent", "#E8913A"),
    "C": ("noshow", "Prioritario", "Priority", "#E0B93E"),
    "D": ("silent", "Seguimiento", "Follow-up", "#8C95A5"),
    "E": ("stable", "Rutina", "Routine", "#3E9E6E"),
}
URGENCIA_A_NIVEL = {"alta": "B", "media": "C", "baja": "E"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@600&display=swap');

:root{
  --navy-800:#192436; --navy-600:#33425E; --navy-200:#C9D1DE; --navy-100:#E4E9F1; --navy-50:#F1F4F9;
  --teal-700:#237873; --teal-500:#3FA7A0; --teal-50:#E9F5F4;
  --canvas:#F4F6FA; --surface:#FFFFFF; --border:#DDE2EA; --border-input:#7E8798;
  --ink-muted:#5B6475; --ink-disabled:#9AA3B2;
}

html, body, [data-testid="stAppViewContainer"], .stApp{
  font-family:'Inter',sans-serif; background:var(--canvas); color:var(--navy-800);
}
header[data-testid="stHeader"]{ background:transparent; }
#MainMenu, footer{ visibility:hidden; }
.block-container{ padding-top:2rem; max-width:1280px; }

/* Tipografía */
h1,h2,h3{ font-family:'Montserrat',sans-serif !important; font-weight:600 !important;
  color:var(--navy-800); letter-spacing:0 !important; }
h1{ font-size:24px !important; line-height:32px !important; }
h2{ font-size:20px !important; line-height:28px !important; }
h3{ font-size:16px !important; line-height:24px !important; }
p, li, label, .stMarkdown{ font-size:14px; line-height:20px; }
[data-testid="stCaptionContainer"], .stCaption{ color:var(--ink-muted); font-size:12px; line-height:16px; }

/* Barra lateral */
[data-testid="stSidebar"]{ background:var(--navy-800); border-right:1px solid var(--navy-600); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3{ color:#FFFFFF; }
[data-testid="stSidebar"] label p, [data-testid="stSidebar"] [data-testid="stCaptionContainer"]{ color:var(--navy-200); }

/* Pestañas: planas, subrayado teal */
.stTabs [role="tablist"]{ background:transparent; border-bottom:1px solid var(--border); gap:4px; padding:0; }
.stTabs [role="tab"]{ border-radius:8px 8px 0 0; padding:.6rem 1rem; font-weight:500; color:var(--ink-muted); }
.stTabs [role="tab"]:hover{ background:var(--navy-50); color:var(--navy-800); }
.stTabs [role="tab"][aria-selected="true"]{ color:var(--teal-700); font-weight:600; background:transparent; }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--teal-700); }

/* Tarjetas: borde, sin sombra, radio 8 */
div[data-testid="stMetric"], div[data-testid="stExpander"], div[data-testid="stAlert"], .ml-card{
  background:var(--surface); border:1px solid var(--border); border-radius:8px; box-shadow:none;
}
div[data-testid="stMetric"]{ padding:16px; }
div[data-testid="stMetricValue"]{ font-family:'Montserrat',sans-serif; font-weight:600; font-size:32px; line-height:40px; }
div[data-testid="stMetricLabel"] p{ color:var(--ink-muted); font-size:12px; }
.ml-card{ padding:16px; margin-bottom:12px; }
.ml-card h4{ font-family:'Montserrat',sans-serif; font-weight:600; font-size:16px; line-height:24px; margin:0 0 4px 0; }
.ml-card .meta{ color:var(--ink-muted); font-size:12px; line-height:16px; }
.ml-bar{ border-left:4px solid var(--border); }

/* Botones */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button, .stLinkButton>a{
  border-radius:8px; min-height:40px; font-weight:600; font-size:14px; transition:background .15s;
}
.stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"], .stButton>button{
  background:var(--teal-700); color:#FFFFFF; border:1px solid var(--teal-700);
}
.stButton>button:hover{ background:#1B605C; border-color:#1B605C; color:#FFFFFF; }
.stButton>button:active{ background:#154B48; border-color:#154B48; }
.stButton>button:focus-visible{ outline:2px solid var(--teal-700); outline-offset:2px; }
.stButton>button:disabled{ background:#EEF1F5; color:var(--ink-disabled); border-color:#EEF1F5; }
.stFormSubmitButton>button{ background:var(--teal-700); color:#FFFFFF; border:1px solid var(--teal-700); }
.stFormSubmitButton>button:hover{ background:#1B605C; color:#FFFFFF; }

/* Campos: borde #7E8798, foco 2 px teal */
.stTextInput input, .stTextArea textarea, .stNumberInput input{ border-radius:8px; }
.stTextInput [data-baseweb="input"], .stTextArea [data-baseweb="textarea"],
.stNumberInput [data-baseweb="input"], .stSelectbox [data-baseweb="select"]>div{
  border:1px solid var(--border-input); border-radius:8px;
}
.stTextInput [data-baseweb="input"]:focus-within, .stTextArea [data-baseweb="textarea"]:focus-within,
.stNumberInput [data-baseweb="input"]:focus-within{ border:2px solid var(--teal-700); }
[data-testid="stSidebar"] .stTextInput [data-baseweb="input"],
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"]>div{ border-color:var(--navy-600); }

/* Badges clínicos: radio completo, 24 px, Inter 600 12 px */
.ml-badge{ display:inline-flex; align-items:center; gap:6px; height:24px; padding:0 8px;
  border-radius:999px; font-size:12px; font-weight:600; line-height:16px; white-space:nowrap; }
.ml-dot{ width:8px; height:8px; border-radius:50%; display:inline-block; }
.ml-risk{ background:#FCEBEB; color:#A12C2C; }   .ml-risk .ml-dot{ background:#D64545; }
.ml-review{ background:#FDF0E2; color:#8C4A0E; } .ml-review .ml-dot{ background:#E8913A; }
.ml-noshow{ background:#FBF4D9; color:#6E5410; } .ml-noshow .ml-dot{ background:#E0B93E; }
.ml-silent{ background:#EEF1F5; color:#4A5366; } .ml-silent .ml-dot{ background:#8C95A5; }
.ml-stable{ background:#E5F3EC; color:#1E6443; } .ml-stable .ml-dot{ background:#3E9E6E; }
.ml-bar-risk{ border-left-color:#D64545; } .ml-bar-review{ border-left-color:#E8913A; }
.ml-bar-noshow{ border-left-color:#E0B93E; } .ml-bar-silent{ border-left-color:#8C95A5; }
.ml-bar-stable{ border-left-color:#3E9E6E; }

/* Aviso de demo */
.ml-demo{ background:var(--teal-50); border:1px solid var(--teal-500); border-radius:8px;
  padding:8px 12px; color:var(--navy-800); font-size:12px; line-height:16px; margin-bottom:16px; }

@media (prefers-reduced-motion: reduce){ *{ transition:none !important; animation:none !important; } }
</style>
"""


def badge_nivel(nivel):
    clase, es, en, _ = NIVELES.get(nivel, ("silent", nivel, nivel, "#8C95A5"))
    return f"<span class='ml-badge ml-{clase}'><span class='ml-dot'></span>{L(es, en)}</span>"


def etiqueta_nivel(nivel):
    _, es, en, _ = NIVELES.get(nivel, ("silent", nivel, nivel, ""))
    return f"{L('Nivel', 'Level')} {nivel} · {L(es, en)}"


def card(html, nivel=None):
    barra = ""
    if nivel in NIVELES:
        barra = f" ml-bar ml-bar-{NIVELES[nivel][0]}"
    st.markdown(f"<div class='ml-card{barra}'>{html}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Textos y datos de demostración
# ---------------------------------------------------------------------------

ESTADOS = {
    "Pendiente": ("Pendiente", "Pending"),
    "En Atencion": ("En atención", "In progress"),
    "En Atención": ("En atención", "In progress"),
    "Revisado": ("Revisado", "Reviewed"),
}


def estado_txt(estado):
    es, en = ESTADOS.get(estado, (estado, estado))
    return L(es, en)


# Traducción de los textos sintéticos de las fichas y la CIE-10.
DATA_EN = {
    "Femenino": "Female", "Masculino": "Male", "No binario": "Non-binary",
    "Prefiero no decirlo": "Prefer not to say", "Sí": "Yes", "No": "No",
    "Hoy": "Today", "Hace 2 días": "2 days ago", "Hace 1 semana": "1 week ago",
    "Hace 3 días": "3 days ago", "Reciente": "Recent", "Nunca": "Never", "Ahora": "Now",
    "Ansiedad generalizada, antecedente de duelo reciente.": "Generalized anxiety; recent bereavement.",
    "Angustia intensa y sensación de presión torácica.": "Severe distress and a feeling of chest pressure.",
    "Palpitaciones, insomnio, llanto frecuente, baja energía.": "Palpitations, insomnia, frequent crying, and low energy.",
    "Sertralina 50 mg 1 vez/día.": "Sertraline 50 mg once daily.",
    "Hipertensión controlada.": "Controlled hypertension.",
    "Ansiedad y tensión durante la semana.": "Anxiety and increased tension this week.",
    "Nerviosismo, irritabilidad, dificultad para concentrarse.": "Nervousness, irritability, and difficulty concentrating.",
    "No refiere medicación actual.": "Reports no current medication.",
    "Episodios descritos como crisis de pánico y preocupación por que vuelvan a ocurrir.": "Episodes described as panic attacks and worry that they will return.",
    "Quiere aprender a manejar episodios de miedo intenso.": "Wants to learn to manage episodes of intense fear.",
    "Palpitaciones y sensación de alarma durante episodios de angustia.": "Palpitations and a sense of alarm during episodes of distress.",
    "Ánimo bajo y pérdida de interés en actividades durante las últimas semanas.": "Low mood and loss of interest in activities over recent weeks.",
    "Consulta por cambios de ánimo y descanso irregular.": "Reports mood changes and irregular rest.",
    "Baja energía, menos interés en actividades y dificultad para dormir.": "Low energy, less interest in activities, and difficulty sleeping.",
    "Sin antecedentes relevantes cargados.": "No relevant medical history entered.",
    "Consulta general.": "General consultation.",
    "Sin síntomas registrados.": "No symptoms recorded.",
    "Sin medicación registrada.": "No medication recorded.",
    "Paciente reporta ánimo muy bajo y ausencia de interés en actividades cotidianas.": "Patient reports very low mood and loss of interest in everyday activities.",
    "Ánimo: muy bajo • Medicación: No • Cita: No puedo asistir": "Mood: very low • Medication: No • Appointment: Unable to attend",
    "Consulta por ansiedad y aumento de tensión durante la semana.": "Reports anxiety and increased tension this week.",
    "Ánimo: regular • Medicación: Sí • Cita: Sí, agendada": "Mood: fair • Medication: Yes • Appointment: Scheduled",
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
}


def td(texto):
    """Traduce datos sintéticos; los textos escritos por el usuario se dejan tal cual."""
    if st.session_state.get("language") == "English":
        return DATA_EN.get(texto, texto)
    return texto


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

PACIENTES_INICIALES = {
    "María González": {
        "edad": 32, "genero": "Femenino",
        "antecedentes": "Ansiedad generalizada, antecedente de duelo reciente.",
        "motivo": "Angustia intensa y sensación de presión torácica.",
        "sintomas": "Palpitaciones, insomnio, llanto frecuente, baja energía.",
        "tratamiento": "Sertralina 50 mg 1 vez/día.", "red_apoyo": "Sí",
        "ultima_revision": "Hoy", "riesgo": "B",
    },
    "Carlos Muñoz": {
        "edad": 41, "genero": "Masculino",
        "antecedentes": "Hipertensión controlada.",
        "motivo": "Ansiedad y tensión durante la semana.",
        "sintomas": "Nerviosismo, irritabilidad, dificultad para concentrarse.",
        "tratamiento": "No refiere medicación actual.", "red_apoyo": "Sí",
        "ultima_revision": "Hace 2 días", "riesgo": "C",
    },
    "Ana Silva": {
        "edad": 28, "genero": "Femenino",
        "antecedentes": "Episodios descritos como crisis de pánico y preocupación por que vuelvan a ocurrir.",
        "motivo": "Quiere aprender a manejar episodios de miedo intenso.",
        "sintomas": "Palpitaciones y sensación de alarma durante episodios de angustia.",
        "tratamiento": "No refiere medicación actual.", "red_apoyo": "Sí",
        "ultima_revision": "Hace 1 semana", "riesgo": "C",
    },
    "Pedro Morales": {
        "edad": 36, "genero": "Masculino",
        "antecedentes": "Ánimo bajo y pérdida de interés en actividades durante las últimas semanas.",
        "motivo": "Consulta por cambios de ánimo y descanso irregular.",
        "sintomas": "Baja energía, menos interés en actividades y dificultad para dormir.",
        "tratamiento": "No refiere medicación actual.", "red_apoyo": "Sí",
        "ultima_revision": "Hace 3 días", "riesgo": "C",
    },
}

CASOS_INICIALES = [
    {
        "id": "WA-101", "nombre": "María González", "telefono": "+56 9 1111 2222",
        "canal": "WhatsApp", "urgencia": "alta", "estado": "Pendiente",
        "resumen": "Paciente reporta ánimo muy bajo y ausencia de interés en actividades cotidianas.",
        "detalle": "Ánimo: muy bajo • Medicación: No • Cita: No puedo asistir",
    },
    {
        "id": "WA-102", "nombre": "Carlos Muñoz", "telefono": "+56 9 3333 4444",
        "canal": "WhatsApp", "urgencia": "media", "estado": "Revisado",
        "resumen": "Consulta por ansiedad y aumento de tensión durante la semana.",
        "detalle": "Ánimo: regular • Medicación: Sí • Cita: Sí, agendada",
    },
]

# Recursos educativos: (es, en) en cada campo de texto.
RECURSOS = [
    {
        "keywords": ("ansiedad", "anxiety", "angustia"),
        "title": ("Ansiedad", "Anxiety"),
        "desc": ("Explicaciones breves sobre síntomas, ansiedad generalizada y estrategias de regulación.",
                 "Short explanations about symptoms, generalized anxiety, and grounding strategies."),
        "support": (
            ["Prueba una pausa breve: observa lo que ocurre a tu alrededor y vuelve la atención a una sensación que te resulte cómoda.",
             "Si te ayuda, respira despacio y sin forzar; detente si notas más malestar.",
             "Anota cuándo aparece la angustia y qué estaba pasando para conversarlo con tu equipo de salud.",
             "No cambies ni suspendas medicamentos sin hablar con quien los indicó."],
            ["Try a brief pause: notice what is around you and bring your attention to a sensation that feels comfortable.",
             "If helpful, breathe slowly without forcing it; stop if it increases your discomfort.",
             "Note when distress appears and what was happening so you can discuss it with your care team.",
             "Do not change or stop medication without speaking with the prescriber."],
        ),
        "query": "ansiedad salud mental explicacion",
    },
    {
        "keywords": ("panico", "ataque de panico", "panic attack"),
        "title": ("Crisis de pánico", "Panic attacks"),
        "desc": ("Información general para comprender las crisis de pánico y conversar sobre ellas con un profesional.",
                 "General information to understand panic attacks and discuss them with a professional."),
        "support": (
            ["Si te sientes a salvo, busca un lugar tranquilo y recuerda que puedes pedir compañía a alguien de confianza.",
             "Intenta describir lo que notas sin juzgarlo; no es necesario forzar la respiración ni hacer ejercicios que te incomoden.",
             "Si es la primera vez, los síntomas son intensos o tienes dolor de pecho/dificultad para respirar, busca evaluación médica."],
            ["If you feel safe, find a calm place and remember you can ask someone you trust to stay with you.",
             "Try describing what you notice without judging it; you do not need to force your breathing or do exercises that feel uncomfortable.",
             "If this is the first episode, symptoms are severe, or you have chest pain or trouble breathing, seek medical assessment."],
        ),
        "query": "crisis de panico salud mental orientacion",
    },
    {
        "keywords": ("depres", "animo bajo", "perdida de interes", "low mood", "loss of interest"),
        "title": ("Depresión", "Depression"),
        "desc": ("Recursos orientativos para reconocer síntomas depresivos y señales de alerta.",
                 "Orientation resources to recognize depressive symptoms and warning signs."),
        "support": (
            ["Cuando cueste empezar, intenta elegir una actividad pequeña y posible para hoy, sin exigirte resolverlo todo.",
             "Cuéntale a alguien de confianza cómo te has sentido y acuerda un momento para hablar con tu equipo de salud.",
             "No cambies ni suspendas medicamentos sin hablar con quien los indicó."],
            ["When getting started feels difficult, try choosing one small, manageable activity for today.",
             "Tell someone you trust how you have been feeling and arrange a time to speak with your care team.",
             "Do not change or stop medication without speaking with the prescriber."],
        ),
        "query": "depresion salud mental explicacion",
    },
    {
        "keywords": ("estres", "stress", "sueño", "sueno", "sleep", "insomnio",
                     "dificultad para dormir", "descanso irregular", "problemas de sueño"),
        "title": ("Estrés y sueño", "Stress and sleep"),
        "desc": ("Videos para acompañar la identificación del estrés y su impacto en el sueño y la atención.",
                 "Videos to support identifying stress and its impact on sleep and attention."),
        "support": (
            ["Observa qué situaciones aumentan el estrés y conversa con tu equipo sobre cambios que sean realistas para ti.",
             "Si es posible, mantén horarios de descanso regulares y reserva un momento tranquilo antes de dormir.",
             "Si el problema persiste o afecta tu día a día, coméntalo con un profesional de salud."],
            ["Notice which situations increase stress and discuss realistic changes with your care team.",
             "If possible, keep regular rest times and set aside a quiet period before bed.",
             "If the problem continues or affects daily life, discuss it with a health professional."],
        ),
        "query": "estres ansiedad sueño salud mental",
    },
    {
        "keywords": ("duelo", "grief", "bereavement", "perdida de un ser querido",
                     "fallecimiento", "muerte de un familiar"),
        "title": ("Duelo y adaptación", "Grief and adaptation"),
        "desc": ("Material orientativo para sostener procesos de duelo, pérdida y reencuadre emocional.",
                 "Orientation material to support grief, loss, and emotional reframing processes."),
        "support": (
            ["El duelo es distinto para cada persona; no hay un plazo único ni una forma correcta de vivirlo.",
             "Busca compañía de alguien de confianza y comparte qué tipo de apoyo te sería útil.",
             "Si el dolor se vuelve abrumador o te impide realizar actividades cotidianas, pide apoyo a un profesional."],
            ["Grief is different for everyone; there is no single timeline or right way to experience it.",
             "Reach out to someone you trust and share what kind of support would help.",
             "If distress feels overwhelming or keeps you from daily activities, seek support from a professional."],
        ),
        "query": "duelo salud mental explicacion",
    },
    {
        "keywords": ("autoestima", "autoconfianza", "self esteem", "self confidence"),
        "title": ("Autoestima y autoconfianza", "Self-esteem and self-confidence"),
        "desc": ("Ideas de reflexión sobre autovaloración, autocrítica y búsqueda de apoyo.",
                 "Reflection ideas about self-worth, self-criticism, and seeking support."),
        "support": (
            ["Observa cómo te hablas cuando algo no resulta y prueba describir la situación con palabras más amables y realistas.",
             "Anota una acción pequeña que hayas logrado hoy, sin compararte con otras personas.",
             "Si la autocrítica afecta tu bienestar, puedes conversarlo con un profesional de salud mental."],
            ["Notice how you speak to yourself when something does not go as planned and try a kinder, more realistic description.",
             "Note one small thing you managed today without comparing yourself to others.",
             "If self-criticism affects your wellbeing, consider discussing it with a mental health professional."],
        ),
        "query": "autoestima salud mental apoyo psicologico",
    },
    {
        "keywords": ("trauma", "estres postraumatico", "post traumatic", "ptsd", "experiencia dificil"),
        "title": ("Estrés tras experiencias difíciles", "Stress after difficult experiences"),
        "desc": ("Material general sobre reacciones al estrés y cómo buscar apoyo de manera segura.",
                 "General material about stress responses and how to seek support safely."),
        "support": (
            ["No tienes que contar detalles de una experiencia difícil si no te sientes preparado/a.",
             "Identifica a una persona o profesional con quien te sientas seguro/a para pedir apoyo.",
             "Evita exponerte por tu cuenta a recuerdos o ejercicios intensos; solicita orientación profesional."],
            ["You do not have to share details of a difficult experience if you do not feel ready.",
             "Identify a person or professional you feel safe with to ask for support.",
             "Avoid confronting memories or intense exercises on your own; ask a professional for guidance."],
        ),
        "query": "estres trauma salud mental apoyo profesional",
    },
    {
        "keywords": ("toc", "obses", "compuls", "ocd", "pensamientos repetitivos", "revisar varias veces", "rituales"),
        "title": ("Trastorno obsesivo-compulsivo", "Obsessive-compulsive disorder"),
        "desc": ("Referencias para entender pensamientos obsesivos, compulsiones y cómo pedir apoyo.",
                 "References to understand obsessive thoughts, compulsions, and how to seek support."),
        "support": (
            ["Anota qué situaciones te preocupan y qué impacto tienen, para compartirlo con un profesional.",
             "Pide orientación a un profesional de salud mental; evita iniciar por tu cuenta cambios o ejercicios que te generen angustia.",
             "No cambies ni suspendas medicamentos sin hablar con quien los indicó."],
            ["Note which situations concern you and how they affect you, so you can share this with a professional.",
             "Ask a mental health professional for guidance; avoid starting changes or exercises that cause distress on your own.",
             "Do not change or stop medication without speaking with the prescriber."],
        ),
        "query": "TOC salud mental explicacion",
    },
]

ANIMOS = [
    ("😄", "Muy bien", "Very good"), ("🙂", "Bien", "Good"), ("😐", "Regular", "Fair"),
    ("😟", "Bajo", "Low"), ("😢", "Muy bajo", "Very low"),
]


def normalizar_texto(texto):
    texto_normalizado = unicodedata.normalize("NFKD", str(texto).casefold())
    return "".join(c for c in texto_normalizado if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------

init_db()

if "demo_cases" not in st.session_state:
    st.session_state.demo_cases = [dict(c) for c in CASOS_INICIALES]
if "pacientes" not in st.session_state:
    st.session_state.pacientes = {k: dict(v) for k, v in PACIENTES_INICIALES.items()}


def perfil_base():
    return {
        "edad": 30, "genero": "Femenino",
        "antecedentes": "Sin antecedentes relevantes cargados.",
        "motivo": "Consulta general.", "sintomas": "Sin síntomas registrados.",
        "tratamiento": "Sin medicación registrada.", "red_apoyo": "Sí",
        "ultima_revision": "Nunca", "riesgo": "E",
    }


# ---------------------------------------------------------------------------
# Barra lateral: navegación y configuración
# ---------------------------------------------------------------------------

st.markdown(CSS, unsafe_allow_html=True)

if LOGO_SIDEBAR.exists():
    st.logo(str(LOGO_SIDEBAR), size="large")

st.sidebar.selectbox("Language / Idioma", LANGS, key="language")

PERFILES = {
    "Paciente": ("Paciente", "Patient"),
    "Enfermería": ("Enfermería", "Nursing"),
    "Equipo tratante": ("Equipo tratante", "Care team"),
}
perfil_demo = st.sidebar.selectbox(
    L("Ver la experiencia como", "View the experience as"),
    list(PERFILES),
    format_func=lambda p: L(*PERFILES[p]),
)
st.sidebar.caption(L(
    "Selector de demo: no es inicio de sesión ni control de acceso.",
    "Demo selector: this is not a login or access control.",
))

NUEVO = "__nuevo__"
opciones_pacientes = list(PACIENTES_INICIALES) + [NUEVO]
paciente_sel = st.sidebar.selectbox(
    L("Paciente de prueba", "Demo patient"),
    opciones_pacientes,
    format_func=lambda p: L("Agregar nuevo paciente", "Add new patient") if p == NUEVO else p,
    key="paciente_seleccionado",
)
if paciente_sel == NUEVO:
    nombre_paciente = st.sidebar.text_input(
        L("Nombre y apellido del nuevo paciente", "New patient's full name"),
        value=L("Juan Pérez", "Juan Perez"),
    ).strip()
    if not nombre_paciente:
        st.sidebar.warning(L("Ingresa un nombre para continuar.", "Enter a name to continue."))
        st.stop()
else:
    nombre_paciente = paciente_sel

if nombre_paciente not in st.session_state.pacientes:
    st.session_state.pacientes[nombre_paciente] = perfil_base()

with st.sidebar.expander(L("Configuración del análisis", "Analysis settings")):
    groq_key = st.text_input("Groq API key", type="password", value="")
    st.caption(L(
        "La clave solo se usa para solicitar el análisis a Groq. No se guarda.",
        "The key is only used to request the analysis from Groq. It is not stored.",
    ))

perfil_actual = st.session_state.pacientes[nombre_paciente]

alertas = obtener_alertas()
if perfil_demo == "Paciente":
    alertas = [a for a in alertas if a[1] == nombre_paciente]


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def encabezado():
    if perfil_demo == "Paciente":
        st.title(L("Tu espacio de bienestar", "Your wellbeing space"))
        st.caption(L(
            "Comparte una actualización y consulta la información de tu ficha de demostración.",
            "Share an update and review the information in your demo record.",
        ))
    else:
        st.title("MindeLine")
        st.caption(L(
            "Ficha clínica y triaje digital · Prototipo de demostración",
            "Clinical record and digital triage · Demo prototype",
        ))
    st.markdown(
        "<div class='ml-demo'>"
        + L("Datos sintéticos. No usar para decisiones clínicas ni con datos reales. "
            "Ante una emergencia, contacta los servicios de emergencia locales.",
            "Synthetic data. Do not use for clinical decisions or with real patient data. "
            "In an emergency, contact local emergency services.")
        + "</div>",
        unsafe_allow_html=True,
    )


FLUJOS = {
    "Paciente": (
        ("Comparte cómo te sientes mediante el simulador de mensajes. Si necesitas ayuda inmediata, "
         "contacta los servicios de emergencia locales o a tu equipo de salud.",
         "Share how you are feeling using the message simulator. If you need immediate help, "
         "contact local emergency services or your healthcare team."),
        [("Compartir una actualización", "Share an update"),
         ("El equipo revisa la solicitud", "The team reviews the request"),
         ("Recibir seguimiento", "Receive follow-up")],
    ),
    "Enfermería": (
        ("Revisa la bandeja, identifica solicitudes pendientes y marca cada caso cuando haya sido revisado.",
         "Review the inbox, identify pending requests, and mark each case once reviewed."),
        [("Revisar casos entrantes", "Review incoming cases"),
         ("Tomar o marcar casos", "Take or mark cases"),
         ("Derivar al equipo tratante cuando corresponda", "Refer to the care team when appropriate")],
    ),
    "Equipo tratante": (
        ("Consulta la ficha, revisa alertas y utiliza los filtros de apoyo como referencia; "
         "valida siempre las decisiones clínicamente.",
         "Review the patient record and alerts. Use support filters as references and always validate decisions clinically."),
        [("Revisar ficha e historial", "Review the record and history"),
         ("Evaluar alertas priorizadas", "Assess prioritized alerts"),
         ("Registrar seguimiento en la ficha", "Record follow-up in the patient record")],
    ),
}


def flujo_de_trabajo():
    descripcion, pasos = FLUJOS[perfil_demo]
    with st.expander(L("Cómo funciona esta demo", "How this demo works")):
        st.write(L(*descripcion))
        for i, columna in enumerate(st.columns(len(pasos)), start=1):
            es, en = pasos[i - 1]
            columna.markdown(
                f"<div class='ml-card'><div class='meta'>{L('Paso', 'Step')} {i}</div>"
                f"<h4>{L(es, en)}</h4></div>",
                unsafe_allow_html=True,
            )


def mostrar_tarjeta_alerta(alerta):
    alerta_id, nombre, fecha, _tipo, transcripcion, nivel, resumen, phq9, estado = alerta
    titulo = f"{etiqueta_nivel(nivel)} · {nombre} · {estado_txt(estado)} · {fecha}"
    with st.expander(titulo):
        if nivel == "A":
            st.error(L(
                "Protocolo de crisis: derivar a SAMU 131 o Salud Responde *4141.",
                "Crisis protocol: contact local emergency services (in Chile: SAMU 131 or Salud Responde *4141) "
                "or the patient's care team immediately.",
            ))
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(badge_nivel(nivel), unsafe_allow_html=True)
            st.write(f"**{L('Transcripción', 'Transcript')}:** “{transcripcion}”")
            st.write(f"**{L('Síntesis', 'Summary')}:** {resumen}")
            st.write(f"**{L('PHQ-9 estimado', 'Estimated PHQ-9')}:** {phq9}")
        with c2:
            if estado == "Pendiente":
                if st.button(L("Tomar caso", "Take case"), key=f"tomar_{alerta_id}",
                             width="stretch"):
                    actualizar_estado_alerta(alerta_id, "En Atencion")
                    st.rerun()


def registrar_resultado(tipo, contenido, trans, json_res):
    guardar_alerta(
        nombre_paciente=nombre_paciente,
        tipo_mensaje=tipo,
        contenido=contenido,
        transcripcion=trans,
        nivel=json_res["nivel_riesgo"],
        resumen=json_res["resumen_clinico"],
        phq9=json_res.get("phq9_estimado", 0),
    )
    st.session_state.pacientes[nombre_paciente]["riesgo"] = json_res["nivel_riesgo"]
    st.session_state.pacientes[nombre_paciente]["ultima_revision"] = "Reciente"


def idioma_api():
    return "en" if st.session_state.language == "English" else "es"


def render_simulador():
    st.subheader(L("Simulador de mensajes", "Message simulator"))
    st.caption(L(
        "Procesa un mensaje de texto o una nota de voz con IA. Requiere conexión a Internet y una Groq API key.",
        "Process a text message or voice note with AI. Requires an Internet connection and a Groq API key.",
    ))
    canales = {"texto": ("Texto", "Text message"), "audio": ("Nota de voz", "Voice note")}
    canal = st.radio(
        L("Canal de entrada", "Input method"), list(canales),
        format_func=lambda c: L(*canales[c]), horizontal=True,
    )
    sin_clave = L("Ingresa la Groq API key en «Configuración del análisis» (barra lateral).",
                  "Enter the Groq API key under “Analysis settings” (sidebar).")

    if canal == "texto":
        texto = st.text_area(
            L("Mensaje del paciente", "Patient message"),
            value=L("Siento mucha angustia y dolor en el pecho, necesito ayuda.",
                    "I feel very anxious and have chest pain. I need help."),
            height=140,
        )
        if st.button(L("Enviar mensaje", "Send message")):
            if not groq_key:
                st.error(sin_clave)
            elif not texto.strip():
                st.error(L("Escribe un mensaje para enviar.", "Write a message to send."))
            else:
                try:
                    with st.spinner(L("Analizando mensaje…", "Analyzing message…")):
                        trans, res = procesar_audio_o_texto(
                            groq_key, texto_ingresado=texto, idioma=idioma_api())
                    registrar_resultado("Texto", texto, trans, res)
                except Exception:
                    st.error(L("No se pudo procesar el mensaje. Revisa la API key y tu conexión, e inténtalo de nuevo.",
                               "The message could not be processed. Check the API key and your connection, then try again."))
                else:
                    st.success(L(f"Alerta registrada para {nombre_paciente}.",
                                 f"Alert recorded for {nombre_paciente}."))
                    st.rerun()
    else:
        archivo = st.file_uploader(
            L("Subir nota de voz (.mp3, .wav, .m4a)", "Upload a voice note (.mp3, .wav, .m4a)"),
            type=["mp3", "wav", "m4a"],
        )
        if archivo and st.button(L("Procesar audio", "Process audio")):
            if not groq_key:
                st.error(sin_clave)
            else:
                ruta = None
                try:
                    sufijo = Path(archivo.name).suffix or ".wav"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
                        tmp.write(archivo.getbuffer())
                        ruta = tmp.name
                    with st.spinner(L("Transcribiendo audio…", "Transcribing audio…")):
                        trans, res = procesar_audio_o_texto(
                            groq_key, audio_file_path=ruta, idioma=idioma_api())
                    registrar_resultado("Audio", "[Nota de voz]", trans, res)
                except Exception:
                    st.error(L("No se pudo procesar el audio. Revisa la API key, el formato del archivo y tu conexión.",
                               "The audio could not be processed. Check the API key, the file format, and your connection."))
                else:
                    st.success(L(f"Audio procesado para {nombre_paciente}.",
                                 f"Audio processed for {nombre_paciente}."))
                    st.rerun()
                finally:
                    if ruta and os.path.exists(ruta):
                        os.remove(ruta)


# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------

encabezado()
flujo_de_trabajo()

if perfil_demo == "Paciente":
    nombres_tabs = [
        L(":material/home: Inicio", ":material/home: Home"),
        L(":material/assignment_ind: Mi ficha", ":material/assignment_ind: My record"),
        L(":material/chat: Enviar mensaje", ":material/chat: Send a message"),
        L(":material/favorite: Mi apoyo", ":material/favorite: My support"),
    ]
    tab_dashboard, tab_ficha, tab_simulador, tab_support = st.tabs(nombres_tabs)
else:
    nombres_tabs = [
        L(":material/dashboard: Resumen", ":material/dashboard: Overview"),
        L(":material/assignment_ind: Ficha clínica", ":material/assignment_ind: Patient record"),
        L(":material/inbox: Triaje", ":material/inbox: Triage"),
        L(":material/stethoscope: Enfermería", ":material/stethoscope: Nursing"),
        L(":material/groups: Equipo tratante", ":material/groups: Care team"),
        L(":material/show_chart: Evolución", ":material/show_chart: Trends"),
        L(":material/chat: Simulador", ":material/chat: Simulator"),
        L(":material/menu_book: Recursos", ":material/menu_book: Resources"),
    ]
    (tab_dashboard, tab_ficha, tab_triaje, tab_enfermeria, tab_tratante,
     tab_analitica, tab_simulador, tab_support) = st.tabs(nombres_tabs)


# --- Resumen --------------------------------------------------------------
with tab_dashboard:
    if perfil_demo == "Paciente":
        st.metric(L("Interacciones totales", "Total interactions"), len(alertas))
        st.info(L(
            "Tus actualizaciones se registran en este perfil de demostración para que el equipo de salud las revise. "
            "Si necesitas ayuda inmediata, contacta los servicios de emergencia locales o a tu equipo de salud.",
            "Your updates are recorded in this demo profile for the care team to review. "
            "If you need immediate help, contact local emergency services or your healthcare team.",
        ))
    else:
        nivel_a = sum(1 for a in alertas if a[5] == "A")
        nivel_b = sum(1 for a in alertas if a[5] == "B")
        pendientes = sum(1 for a in alertas if a[8] == "Pendiente")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric(L("Interacciones totales", "Total interactions"), len(alertas))
        d2.metric(L("Nivel A · Emergencia", "Level A · Emergency"), nivel_a)
        d3.metric(L("Nivel B · Urgencia", "Level B · Urgent"), nivel_b)
        d4.metric(L("Pendientes", "Pending"), pendientes)

        st.write("")
        izquierda, derecha = st.columns([2, 1])
        with izquierda:
            st.subheader(L("Estado clínico actual", "Current clinical status"))
            if alertas:
                _id, nom, fecha, _t, _tr, nivel, resumen, _p, estado = alertas[0]
                card(
                    f"<h4>{nom}</h4>"
                    f"<div class='meta'>{estado_txt(estado)} · {fecha}</div>"
                    f"<p style='margin:8px 0'>{resumen}</p>{badge_nivel(nivel)}",
                    nivel,
                )
            else:
                st.info(L(
                    "Aún no hay alertas. Envía un mensaje desde el simulador para registrar la primera.",
                    "No alerts yet. Send a message from the simulator to record the first one.",
                ))
        with derecha:
            st.subheader(L("Paciente activo", "Active patient"))
            riesgo = perfil_actual.get("riesgo", "E")
            card(
                f"<h4>{nombre_paciente}</h4>"
                f"<div class='meta'>{L('Edad', 'Age')}: {perfil_actual.get('edad', 0)} "
                f"{L('años', 'years')} · {L('Red de apoyo', 'Support network')}: "
                f"{td(perfil_actual.get('red_apoyo', 'No'))}</div>"
                f"<div style='margin-top:8px'>{badge_nivel(riesgo)}</div>",
                riesgo,
            )


# --- Ficha clínica --------------------------------------------------------
with tab_ficha:
    st.subheader(L(f"Ficha clínica de {nombre_paciente}", f"Clinical record for {nombre_paciente}"))
    cols = st.columns(2 if perfil_demo == "Paciente" else 4)
    cols[0].metric(L("Edad", "Age"), f"{perfil_actual.get('edad', 0)} {L('años', 'years')}")
    cols[1].metric(L("Género", "Gender"), td(perfil_actual.get("genero", "-")))
    if perfil_demo != "Paciente":
        cols[2].metric(L("Última revisión", "Last review"), td(perfil_actual.get("ultima_revision", "Nunca")))
        cols[3].metric(L("Riesgo actual", "Current risk"), perfil_actual.get("riesgo", "E"))

    info1, info2 = st.columns(2)
    with info1:
        st.markdown(f"**{L('Antecedentes relevantes', 'Relevant medical history')}**")
        st.write(td(perfil_actual.get("antecedentes", "")))
        st.markdown(f"**{L('Motivo de consulta', 'Reason for visit')}**")
        st.write(td(perfil_actual.get("motivo", "")))
        st.markdown(f"**{L('Síntomas principales', 'Main symptoms')}**")
        st.write(td(perfil_actual.get("sintomas", "")))
    with info2:
        st.markdown(f"**{L('Tratamiento / medicación', 'Treatment / medication')}**")
        st.write(td(perfil_actual.get("tratamiento", "")))
        st.markdown(f"**{L('Red de apoyo', 'Support network')}**")
        st.write(td(perfil_actual.get("red_apoyo", "No")))
        if perfil_demo != "Paciente":
            estable = perfil_actual.get("riesgo", "E") in ("D", "E")
            st.markdown(f"**{L('Estado general', 'Overall status')}**")
            st.markdown(
                badge_nivel("E" if estable else perfil_actual.get("riesgo", "C")),
                unsafe_allow_html=True,
            )

    if perfil_demo != "Paciente":
        st.subheader(L("Resumen", "Summary"))
        motivo = td(perfil_actual.get("motivo", "")).rstrip(". ")
        sintomas = td(perfil_actual.get("sintomas", "")).rstrip(". ")
        st.info(L(
            f"Paciente {nombre_paciente} ({perfil_actual.get('edad', 0)} años), con motivo: {motivo}. "
            f"Actualmente presenta: {sintomas}. Revisa el nivel {perfil_actual.get('riesgo', 'E')} "
            "y refuerza el seguimiento si corresponde.",
            f"Patient {nombre_paciente} ({perfil_actual.get('edad', 0)} years old), reason: {motivo}. "
            f"Current symptoms: {sintomas}. Review risk level {perfil_actual.get('riesgo', 'E')} "
            "and provide follow-up as appropriate.",
        ))

    with st.expander(L("Editar ficha", "Edit record")):
        generos = ["Femenino", "Masculino", "No binario", "Prefiero no decirlo"]
        genero_actual = perfil_actual.get("genero", "Femenino")
        with st.form("form_ficha"):
            f1, f2 = st.columns(2)
            edad = f1.number_input(L("Edad", "Age"), 0, 120, int(perfil_actual.get("edad", 30)))
            genero = f2.selectbox(
                L("Género", "Gender"), generos,
                index=generos.index(genero_actual) if genero_actual in generos else 0,
                format_func=td,
            )
            antecedentes = st.text_area(L("Antecedentes relevantes", "Relevant medical history"),
                                        value=perfil_actual.get("antecedentes", ""))
            motivo_n = st.text_area(L("Motivo de consulta", "Reason for visit"),
                                    value=perfil_actual.get("motivo", ""))
            sintomas_n = st.text_area(L("Síntomas principales", "Main symptoms"),
                                      value=perfil_actual.get("sintomas", ""))
            tratamiento = st.text_area(L("Tratamiento / medicación", "Treatment / medication"),
                                       value=perfil_actual.get("tratamiento", ""))
            red_apoyo = st.radio(
                L("Red de apoyo", "Support network"), ["Sí", "No"], horizontal=True,
                index=0 if perfil_actual.get("red_apoyo", "Sí") == "Sí" else 1, format_func=td,
            )
            guardar = st.form_submit_button(L("Guardar ficha", "Save record"))
        if guardar:
            st.session_state.pacientes[nombre_paciente] = {
                "edad": edad, "genero": genero, "antecedentes": antecedentes,
                "motivo": motivo_n, "sintomas": sintomas_n, "tratamiento": tratamiento,
                "red_apoyo": red_apoyo, "ultima_revision": "Ahora",
                "riesgo": perfil_actual.get("riesgo", "E"),
            }
            st.success(L(f"Ficha actualizada para {nombre_paciente}.",
                         f"Record updated for {nombre_paciente}."))
            st.rerun()


# --- Triaje (equipo) ------------------------------------------------------
if perfil_demo != "Paciente":
    with tab_triaje:
        st.subheader(L("Triaje clínico", "Clinical triage"))
        st.caption(L(
            "La clasificación automática es orientativa y no sustituye la evaluación profesional.",
            "Automatic classification is indicative and does not replace professional assessment.",
        ))
        t1, t2, t3, t4 = st.columns(4)
        t1.metric(L("Interacciones totales", "Total interactions"), len(alertas))
        t2.metric(L("Emergencias nivel A", "Level A emergencies"), sum(1 for a in alertas if a[5] == "A"))
        t3.metric(L("Urgencias nivel B", "Level B urgent cases"), sum(1 for a in alertas if a[5] == "B"))
        t4.metric(L("Casos pendientes", "Pending cases"), sum(1 for a in alertas if a[8] == "Pendiente"))
        niveles_sel = st.multiselect(
            L("Filtrar por nivel", "Filter by level"), list(NIVELES), default=list(NIVELES),
            format_func=etiqueta_nivel,
        )
        visibles = [a for a in alertas if a[5] in niveles_sel]
        if not visibles:
            st.info(L("No hay alertas para este filtro.", "No alerts match this filter."))
        for alerta in visibles:
            mostrar_tarjeta_alerta(alerta)


# --- Enfermería -----------------------------------------------------------
if perfil_demo != "Paciente":
    with tab_enfermeria:
        st.subheader(L("Bandeja de enfermería", "Nursing inbox"))
        st.caption(L(
            "Los casos recibidos por WhatsApp o por el simulador se revisan aquí antes de su derivación.",
            "Cases received through WhatsApp or the simulator are reviewed here before referral.",
        ))
        urgencias = {"alta": ("Alta", "High"), "media": ("Media", "Medium"), "baja": ("Baja", "Low")}
        for caso in st.session_state.demo_cases:
            nivel = URGENCIA_A_NIVEL.get(caso["urgencia"], "D")
            u_es, u_en = urgencias.get(caso["urgencia"], (caso["urgencia"], caso["urgencia"]))
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            with c1:
                card(
                    f"<h4>{caso['nombre']}</h4>"
                    f"<div class='meta'>{caso['canal']} · {caso['telefono']} · {caso['id']}</div>"
                    f"<p style='margin:8px 0 4px'>{td(caso['resumen'])}</p>"
                    f"<div class='meta'>{td(caso['detalle'])}</div>"
                    f"<div style='margin-top:8px;display:flex;gap:8px;flex-wrap:wrap'>"
                    f"{badge_nivel(nivel)}"
                    f"<span class='ml-badge ml-silent'>{L('Urgencia', 'Urgency')}: {L(u_es, u_en)}</span>"
                    f"<span class='ml-badge ml-silent'>{estado_txt(caso['estado'])}</span></div>",
                    nivel,
                )
            with c2:
                if caso["estado"] != "Revisado":
                    if st.button(L("Marcar como revisado", "Mark as reviewed"),
                                 key=f"rev_{caso['id']}", width="stretch"):
                        caso["estado"] = "Revisado"
                        st.rerun()
        st.subheader(L("Casos registrados en MindeLine", "Cases recorded in MindeLine"))
        if not alertas:
            st.info(L("Aún no hay casos registrados desde el simulador.",
                      "No cases have been recorded from the simulator yet."))
        else:
            filas = [{
                L("Paciente", "Patient"): a[1],
                L("Fecha", "Date"): a[2],
                L("Nivel", "Level"): etiqueta_nivel(a[5]),
                L("Estado", "Status"): estado_txt(a[8]),
                L("Resumen", "Summary"): a[6],
            } for a in alertas]
            st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)


# --- Equipo tratante ------------------------------------------------------
if perfil_demo != "Paciente":
    with tab_tratante:
        st.subheader(L("Filtro de solicitudes médicas · CIE-10", "Medical request filter · ICD-10"))
        st.caption(L(
            "Prototipo de apoyo para el equipo tratante. Datos de ejemplo; no reemplazan la validación clínica oficial.",
            "Decision-support prototype for the care team. Sample data only; it does not replace clinical review.",
        ))
        TODOS = "__todos__"
        f1, f2, f3 = st.columns(3)
        grupos = {g["id"]: g for g in CIE10_DATA}
        grupo_id = f1.selectbox(
            L("1. Grupo / capítulo", "1. Group / chapter"), [TODOS] + list(grupos),
            format_func=lambda i: L("Todos los grupos", "All groups") if i == TODOS
            else f"{i} · {td(grupos[i]['nombre'])}",
        )
        grupos_sel = CIE10_DATA if grupo_id == TODOS else [grupos[grupo_id]]
        categorias = {c["id"]: c for g in grupos_sel for c in g["categories"]}
        cat_id = f2.selectbox(
            L("2. Categoría diagnóstica", "2. Diagnostic category"), [TODOS] + list(categorias),
            format_func=lambda i: L("Todas las categorías", "All categories") if i == TODOS
            else f"{i} · {td(categorias[i]['nombre'])}",
        )
        cats_sel = list(categorias.values()) if cat_id == TODOS else [categorias[cat_id]]
        subcats = {s["code"]: s for c in cats_sel for s in c["subcategories"]}
        sub_id = f3.selectbox(
            L("3. Subcategoría específica", "3. Specific subcategory"), [TODOS] + list(subcats),
            format_func=lambda i: L("Todas las subcategorías", "All subcategories") if i == TODOS
            else f"{i} · {td(subcats[i]['name'])}",
        )
        subs_sel = list(subcats.values()) if sub_id == TODOS else [subcats[sub_id]]
        if subs_sel:
            df = pd.DataFrame([{
                L("Código", "Code"): s["code"], L("Nombre", "Name"): td(s["name"]),
                L("Casos", "Cases"): s["count"],
            } for s in subs_sel])
            st.dataframe(df, width="stretch", hide_index=True)
            st.caption(L(
                f"Se muestran {len(df)} registros de ejemplo con {int(df.iloc[:, 2].sum())} casos en total. "
                "Estos recuentos no corresponden a un expediente clínico real.",
                f"Showing {len(df)} sample entries with {int(df.iloc[:, 2].sum())} cases in total. "
                "These counts do not represent real patient records.",
            ))
        else:
            st.info(L("Sin resultados para este filtro. Elige otra combinación.",
                      "No results for this filter. Choose another combination."))

        st.subheader(L("Recursos educativos en video", "Educational video resources"))
        st.caption(L(
            "Material breve y orientativo para trastornos frecuentes de salud mental. Este contenido es educativo y no reemplaza la evaluación clínica.",
            "Short, supportive material for common mental health conditions. This content is educational and does not replace clinical assessment.",
        ))
        for r in RECURSOS:
            with st.expander(L(*r["title"])):
                st.write(L(*r["desc"]))
                st.link_button(
                    L("Ver videos en YouTube", "Watch videos on YouTube"),
                    f"https://www.youtube.com/results?search_query={quote_plus(r['query'])}",
                    key=f"yt_{r['query']}",
                )


# --- Evolución ------------------------------------------------------------
if perfil_demo != "Paciente":
    with tab_analitica:
        st.subheader(L("Evolución por nivel de riesgo", "Risk-level trends"))
        todas = obtener_alertas()
        pacientes_con_datos = list(dict.fromkeys(a[1] for a in todas)) or [nombre_paciente]
        elegido = st.selectbox(
            L("Paciente", "Patient"), pacientes_con_datos,
            index=pacientes_con_datos.index(nombre_paciente) if nombre_paciente in pacientes_con_datos else 0,
        )
        historial = [a for a in todas if a[1] == elegido]
        if not historial:
            st.info(L(
                "No hay datos suficientes para mostrar la evolución. Registra una primera alerta desde el simulador.",
                "There is not enough data to display trends. Record a first alert from the simulator.",
            ))
        else:
            df = pd.DataFrame(historial, columns=[
                "id", "nombre", "fecha", "tipo", "transcripcion", "nivel", "resumen", "phq9", "estado"])
            conteo = df.groupby("nivel").size().reindex(list(NIVELES), fill_value=0).reset_index()
            conteo.columns = ["nivel", "cantidad"]
            conteo["etiqueta"] = conteo["nivel"].map(etiqueta_nivel)
            fig = px.bar(
                conteo, x="etiqueta", y="cantidad", color="nivel",
                color_discrete_map={k: v[3] for k, v in NIVELES.items()},
                labels={"etiqueta": L("Nivel", "Level"), "cantidad": L("Cantidad", "Count")},
                title=L(f"Alertas por nivel · {elegido}", f"Alerts by level · {elegido}"),
            )
            fig.update_layout(
                showlegend=False, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif", color="#192436"),
                margin=dict(l=16, r=16, t=48, b=16),
            )
            fig.update_yaxes(gridcolor="#DDE2EA", dtick=1)
            st.plotly_chart(fig, width="stretch")
            tabla = df[["fecha", "nivel", "resumen", "estado"]].copy()
            tabla["estado"] = tabla["estado"].map(estado_txt)
            tabla.columns = [L("Fecha", "Date"), L("Nivel", "Level"),
                             L("Resumen", "Summary"), L("Estado", "Status")]
            st.dataframe(tabla, width="stretch", hide_index=True)


# --- Simulador ------------------------------------------------------------
with tab_simulador:
    render_simulador()


# --- Apoyo / Recursos -----------------------------------------------------
with tab_support:
    if perfil_demo == "Paciente":
        st.subheader(L("Apoyo para ti", "Support for you"))
        st.caption(L(
            "Los recursos se relacionan con temas de tu ficha de demostración. Son educativos, no un diagnóstico ni un plan de tratamiento.",
            "Resources are matched to topics in your demo record. They are educational, not a diagnosis or treatment plan.",
        ))
        st.markdown(f"**{L('¿Cómo te sientes ahora?', 'How are you feeling right now?')}**")
        st.caption(L("Elige la opción que mejor describa cómo te sientes. No hay respuestas correctas o incorrectas.",
                     "Choose the option that best describes how you feel. There are no right or wrong answers."))
        with st.form("form_checkin_animo"):
            animo = st.radio(
                L("Ánimo actual", "Current mood"), [a[0] for a in ANIMOS], horizontal=True,
                index=2, label_visibility="collapsed",
                format_func=lambda e: next(f"{a[0]} {L(a[1], a[2])}" for a in ANIMOS if a[0] == e),
            )
            guardar_animo = st.form_submit_button(L("Guardar cómo me siento", "Save my check-in"))
        if guardar_animo:
            st.session_state["patient_mood_checkin"] = animo
        if "patient_mood_checkin" in st.session_state:
            st.success(L(
                f"Gracias por compartirlo: {st.session_state['patient_mood_checkin']}. "
                "Queda solo en esta sesión de demostración y no se envía al equipo de salud.",
                f"Thanks for sharing: {st.session_state['patient_mood_checkin']}. "
                "This stays in this demo session and is not sent to the care team.",
            ))
    else:
        st.subheader(L(f"Recursos de apoyo · {nombre_paciente}", f"Support resources · {nombre_paciente}"))
        st.caption(L(
            "Los recursos se relacionan con la ficha del paciente seleccionado y son solo orientativos; valídalos con el equipo tratante.",
            "Resources are matched to the selected patient's record for educational reference only; validate them with the care team.",
        ))

    texto_ficha = normalizar_texto(" ".join(
        str(perfil_actual.get(c, "")) for c in ("antecedentes", "motivo", "sintomas")))
    relacionados = [
        r for r in RECURSOS
        if any(normalizar_texto(k) in texto_ficha for k in r["keywords"])
    ]
    if not relacionados:
        st.info(L(
            "No hay recursos relacionados con los temas de esta ficha. Actualiza la ficha para ver sugerencias.",
            "No resources match the topics in this record. Update the record to see suggestions.",
        ))
    for r in relacionados:
        titulo = L(*r["title"])
        puntos = r["support"][1] if st.session_state.language == "English" else r["support"][0]
        items = "".join(f"<li>{p}</li>" for p in puntos)
        card(
            f"<h4>{titulo}</h4><div class='meta'>{L(*r['desc'])}</div>"
            f"<p style='margin:12px 0 4px;font-weight:600'>{L('Ideas de apoyo general', 'General support ideas')}</p>"
            f"<ul style='margin:0 0 0 18px'>{items}</ul>"
        )
        st.link_button(
            L("Ver videos en YouTube", "Watch videos on YouTube"),
            f"https://www.youtube.com/results?search_query={quote_plus(r['query'])}",
        )
    texto_sintomas = normalizar_texto(
        f"{perfil_actual.get('motivo', '')} {perfil_actual.get('sintomas', '')}")
    if any(t in texto_sintomas for t in ("dolor en el pecho", "presion toracica", "chest pain")):
        st.warning(L(
            "El dolor o la presión en el pecho no deben atribuirse automáticamente a la ansiedad. "
            "Si son nuevos o intensos, o aparecen con dificultad para respirar o desmayo, busca atención médica urgente.",
            "Chest pain should not automatically be attributed to anxiety. For new or severe chest pain, "
            "trouble breathing, or fainting, seek urgent medical care.",
        ))
    st.caption(L(
        "Estas ideas generales no reemplazan la atención profesional. No cambies medicamentos sin hablar con quien los indicó. "
        "Si hay peligro inmediato, contacta los servicios de emergencia locales (en Chile: SAMU 131 o Salud Responde *4141) o al equipo de salud.",
        "These general ideas do not replace professional care. Do not change medication without talking to the prescriber. "
        "For immediate danger, contact local emergency services (in Chile: SAMU 131 or Salud Responde *4141) or the care team.",
    ))
