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
from db import MemoryStore
from security import Principal
from access_ui import gate
from html import escape
from backend_ai import validate_audio
from uuid import uuid4

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

authenticated_principal, server_config = gate()
DEMO = authenticated_principal is None

LANGS = ["Español", "English"]
if "language" not in st.session_state:
    st.session_state.language = "Español"


UI_EN = st.session_state.get("language") == "English"


def L(es, en):
    """Texto de interfaz según el idioma elegido."""
    return en if UI_EN else es


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
div[data-testid="stAlertContentWarning"] p{ color:var(--navy-800) !important; }
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

@media (max-width: 640px){
  .block-container{padding-left:1rem;padding-right:1rem;}
  .stTabs [role="tablist"]{overflow-x:auto;}
  .stButton>button,.stFormSubmitButton>button,.stLinkButton>a{min-height:44px;}
  .ml-card{overflow-wrap:anywhere;}
}
@media (prefers-reduced-motion: reduce){ *{ transition:none !important; animation:none !important; } }
</style>
"""


def badge_nivel(nivel):
    clase, es, en, _ = NIVELES.get(nivel, ("silent", "Sin evaluar", "Unassessed", "#8C95A5"))
    return f"<span class='ml-badge ml-{clase}'><span class='ml-dot'></span>{L(es, en)}</span>"


def etiqueta_nivel(nivel):
    if nivel not in NIVELES:
        return L("Sin evaluar", "Unassessed")
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
    if UI_EN:
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

@st.cache_resource
def shared_store():
    return MemoryStore(PACIENTES_INICIALES)

if DEMO:
    if '_demo_store' not in st.session_state:
        st.session_state['_demo_store'] = MemoryStore(PACIENTES_INICIALES)
    store = st.session_state['_demo_store']
else:
    store = shared_store()

if "demo_cases" not in st.session_state:
    st.session_state.demo_cases = [dict(c) for c in CASOS_INICIALES]



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

if DEMO:
    st.session_state.setdefault('_demo_identity', uuid4().hex)
    perfil_demo = st.sidebar.selectbox(
        L("Ver la experiencia como", "View the experience as"),
        ["Paciente", "Enfermería", "Equipo tratante"], key="perfil_demo_seleccionado")
    st.sidebar.caption(L("Selector de demostración; no autentica usuarios.", "Demo selector; does not authenticate users."))
    # The session's demo repository never shares data with another browser session.
    known = st.session_state.setdefault('_demo_names', list(PACIENTES_INICIALES))
    principal = Principal(st.session_state['_demo_identity'] + ':' + perfil_demo,
                          perfil_demo, frozenset(known), True)
    paciente_sel = st.sidebar.selectbox(L("Paciente de prueba", "Demo patient"), known + ["__nuevo__"],
        format_func=lambda x: L("Agregar paciente ficticio", "Add synthetic patient") if x=="__nuevo__" else x,
        key="paciente_seleccionado")
    if paciente_sel == "__nuevo__":
        nombre_paciente = st.sidebar.text_input(L("Nombre ficticio", "Synthetic name"), max_chars=100).strip()
        if not nombre_paciente: st.stop()
        if nombre_paciente not in known:
            try:
                store.add_demo_patient(principal, nombre_paciente, perfil_base())
            except (ValueError, PermissionError):
                st.error(L("No se pudo agregar el paciente.", "Could not add patient.")); st.stop()
            known.append(nombre_paciente)
        principal = Principal(principal.user_id, perfil_demo, frozenset(known), True)
    else:
        nombre_paciente = paciente_sel
else:
    principal = authenticated_principal
    perfil_demo = principal.role
    authorized_patients = store.patients(principal)
    if not authorized_patients:
        st.error(L("No hay pacientes asignados disponibles.", "No assigned patients are available.")); st.stop()
    nombre_paciente = st.sidebar.selectbox(L("Paciente asignado", "Assigned patient"), sorted(authorized_patients), key="paciente_seleccionado")

if perfil_demo == 'Paciente':
    principal = Principal(principal.user_id, principal.role, frozenset({nombre_paciente}), principal.demo)
st.session_state.pacientes = store.patients(principal)
perfil_actual = st.session_state.pacientes[nombre_paciente]
perfil_actual['riesgo'] = store.open_risk(principal, nombre_paciente)
groq_key = os.environ.get('GROQ_API_KEY', server_config.get('groq', {}).get('api_key', ''))
if DEMO and not groq_key:
    with st.sidebar.expander(L("Configuración del análisis", "Analysis settings")):
        groq_key = st.text_input("Groq API key", type="password")
        st.caption(L("Solo datos ficticios. La clave se mantiene en esta sesión.", "Synthetic data only. The key stays in this session."))

def obtener_alertas():
    return store.alerts(principal)

alertas = obtener_alertas()
st.sidebar.caption(L("Almacenamiento temporal: se pierde al reiniciar.", "Temporary storage: lost on restart."))


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


def idioma_api():
    return "en" if st.session_state.language == "English" else "es"


def analyze_request(rid):
    record = store.begin_analysis(principal, rid)
    path = None
    try:
        kwargs = dict(texto_ingresado=record['contenido'], idioma=idioma_api(),
                      model=server_config.get('groq', {}).get('model'))
        if record['tipo_mensaje'] == 'Audio':
            with tempfile.NamedTemporaryFile(delete=False, suffix=record['suffix']) as tmp:
                tmp.write(record['audio'])
                path = tmp.name
            kwargs = dict(audio_file_path=path, idioma=idioma_api(),
                          model=server_config.get('groq', {}).get('model'))
        transcript, result = procesar_audio_o_texto(groq_key, **kwargs)
        store.finish_analysis(principal, rid, transcript, result)
    except Exception:
        # Never expose provider exceptions, keys or message text in logs/UI.
        store.fail_analysis(principal, rid)
        return False
    finally:
        if path and os.path.exists(path): os.remove(path)
    return True


def mostrar_tarjeta_alerta(alerta):
    rid, nombre, fecha, tipo, transcripcion, nivel, resumen, _, estado = alerta
    record = store.get(principal, rid)
    with st.expander(f"{etiqueta_nivel(nivel)} · {nombre} · {estado_txt(estado)} · {fecha}"):
        st.caption(L("Sugerencia automática sin validar clínicamente.", "Automated suggestion, not clinically validated."))
        if nivel == 'A':
            st.error(L("Esta demo no contacta servicios ni envía alertas de emergencia. Ante peligro real, contacta los servicios de emergencia locales.",
                       "This demo does not contact services or send emergency alerts. For real danger, contact local emergency services."))
        st.markdown(badge_nivel(nivel), unsafe_allow_html=True)
        st.text(transcripcion or record['contenido'])
        st.text(resumen)
        if record['alerta_frase']:
            st.write(L("Frase de respaldo:", "Supporting phrase:")); st.text(record['alerta_frase'])
        status_labels = {'pending': L('Pendiente de análisis','Awaiting analysis'),
                         'processing': L('Analizando','Analyzing'),
                         'failed': L('Análisis fallido; requiere revisión','Analysis failed; review required'),
                         'complete': L('Análisis disponible','Analysis available')}
        st.write(status_labels[record['analysis']])
        if record['model']: st.caption(f"{record['model']} · {record['prompt_version']}")
        if estado == 'Pendiente':
            if st.button(L('Tomar caso','Take case'),key='take_'+rid):
                try:
                    store.transition(principal,rid,'En Atencion')
                    st.rerun()
                except (PermissionError,ValueError):
                    st.warning(L('El caso cambió. Actualiza la vista.','The case changed. Refresh the view.'))
        elif estado == 'En Atencion':
            st.write(L('Responsable:', 'Assigned reviewer:'),record['responsable'])
            if record['responsable'] == principal.user_id:
                note = st.text_area(L('Nota de revisión y acción realizada','Review note and action taken'),key='note_'+rid,max_chars=2000)
                if st.button(L('Cerrar como revisado','Close as reviewed'),key='close_'+rid):
                    try:
                        store.transition(principal,rid,'Revisado',note)
                        st.rerun()
                    except (PermissionError,ValueError):
                        st.warning(L('Añade una nota de al menos 3 caracteres y espera a que termine el análisis.',
                                     'Add a note of at least 3 characters and wait for analysis to finish.'))
        if record['note']: st.text(record['note'])
        if estado != 'Revisado' and record['analysis'] in {'pending','failed'}:
            if st.button(L('Reintentar análisis','Retry analysis'),key='retry_'+rid,disabled=not bool(groq_key) or not record['allow_ai']):
                with st.spinner(L('Analizando…','Analyzing…')):
                    try: analyze_request(rid)
                    except (ValueError,PermissionError):
                        st.warning(L('Reintento no disponible: espera 15 segundos; máximo 5 intentos.', 'Retry unavailable: wait 15 seconds; maximum 5 attempts.'))
                st.rerun()
        with st.expander(L('Historial de acciones (temporal)','Action history (temporary)')):
            st.dataframe(pd.DataFrame(store.audit(principal,rid)),hide_index=True)


def render_simulador():
    st.subheader(L('Enviar actualización de prueba','Send a test update'))
    st.caption(L('Solo datos ficticios. El análisis envía texto o audio a Groq.',
                 'Synthetic data only. Analysis sends text or audio to Groq.'))
    channel = st.radio(L('Canal de entrada','Input method'),['Texto','Audio'],horizontal=True,
                       format_func=lambda c: L('Texto','Text') if c=='Texto' else L('Audio','Audio'))
    text = st.text_area(L('Mensaje ficticio','Synthetic message'),max_chars=8000) if channel=='Texto' else ''
    file = st.file_uploader(L('Audio ficticio: máximo 5 MiB','Synthetic audio: maximum 5 MiB'),type=['mp3','wav','m4a']) if channel=='Audio' else None
    consent = st.checkbox(L('Confirmo que son datos ficticios y autorizo enviarlos a Groq para analizarlos.',
                            'I confirm this is synthetic data and agree to send it to Groq for analysis.'))
    if st.button(L('Registrar actualización','Record update')):
        audio, suffix = None, None
        try:
            if channel=='Audio':
                if file is None: raise ValueError('Missing file')
                audio,suffix=file.getvalue(),Path(file.name).suffix.lower()
                validate_audio(audio,suffix)
            rid=store.submit(principal,nombre_paciente,channel,text if channel=='Texto' else '[Audio]',audio=audio,suffix=suffix,allow_ai=consent)
        except (ValueError,PermissionError):
            st.error(L('No se pudo registrar. Revisa el contenido, formato y límite de tamaño o capacidad.',
                       'Could not record. Check the content, format, size or capacity limit.'))
            return
        record=store.get(principal,rid)
        if consent and groq_key and record['analysis']=='pending':
            with st.spinner(L('Analizando…','Analyzing…')):
                try: analyze_request(rid)
                except (ValueError,PermissionError): pass
        st.session_state['_submission_notice']=rid
        st.rerun()
    if st.session_state.get('_submission_notice'):
        try:
            record=store.get(principal,st.session_state['_submission_notice'])
            if record['nombre_paciente']==nombre_paciente:
                if record['analysis']=='complete':
                    st.success(L('Actualización registrada y analizada. Pendiente de revisión profesional.',
                                 'Update recorded and analyzed. Awaiting professional review.'))
                else:
                    st.warning(L('Actualización registrada en memoria, sin análisis válido. El equipo puede revisarla.',
                                 'Update recorded in memory without a valid analysis. The team can review it.'))
        except (PermissionError,KeyError): pass


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
            st.subheader(L("Última actualización recibida", "Latest received update"))
            if alertas:
                _id, nom, fecha, _t, _tr, nivel, resumen, _p, estado = alertas[0]
                card(
                    f"<h4>{escape(nom)}</h4>"
                    f"<div class='meta'>{estado_txt(estado)} · {fecha}</div>"
                    f"<p style='margin:8px 0'>{escape(resumen)}</p>{badge_nivel(nivel)}",
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
                f"<h4>{escape(nombre_paciente)}</h4>"
                f"<div class='meta'>{L('Edad', 'Age')}: {perfil_actual.get('edad', 0)} "
                f"{L('años', 'years')} · {L('Red de apoyo', 'Support network')}: "
                f"{escape(td(perfil_actual.get('red_apoyo', 'No')))}</div>"
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
        cols[3].metric(L("Prioridad abierta", "Open priority"), perfil_actual.get("riesgo", "E"))

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
            st.markdown(f"**{L('Prioridad de alertas abiertas', 'Open alert priority')}**")
            st.markdown(
                badge_nivel(perfil_actual.get("riesgo", "Sin evaluar")),
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

    if perfil_demo != "Paciente":
        with st.expander(L("Editar ficha", "Edit record")):
            snapshot_key = '_edit_' + nombre_paciente
            editing_profile = st.session_state.setdefault(snapshot_key, dict(perfil_actual))
            if st.button(L('Recargar ficha para editar', 'Reload record for editing'), key='reload_'+nombre_paciente):
                st.session_state.pop(snapshot_key, None)
                st.rerun()
            generos = ["Femenino", "Masculino", "No binario", "Prefiero no decirlo"]
            genero_actual = editing_profile.get("genero", "Femenino")
            with st.form("form_ficha_" + nombre_paciente + str(editing_profile["_version"])):
                f1, f2 = st.columns(2)
                edad = f1.number_input(L("Edad", "Age"), 0, 120, int(editing_profile.get("edad", 30)))
                genero = f2.selectbox(
                    L("Género", "Gender"), generos,
                    index=generos.index(genero_actual) if genero_actual in generos else 0,
                    format_func=td,
                )
                antecedentes = st.text_area(L("Antecedentes relevantes", "Relevant medical history"),
                                            value=editing_profile.get("antecedentes", ""))
                motivo_n = st.text_area(L("Motivo de consulta", "Reason for visit"),
                                        value=editing_profile.get("motivo", ""))
                sintomas_n = st.text_area(L("Síntomas principales", "Main symptoms"),
                                          value=editing_profile.get("sintomas", ""))
                tratamiento = st.text_area(L("Tratamiento / medicación", "Treatment / medication"),
                                           value=editing_profile.get("tratamiento", ""))
                red_apoyo = st.radio(
                    L("Red de apoyo", "Support network"), ["Sí", "No"], horizontal=True,
                    index=0 if editing_profile.get("red_apoyo", "Sí") == "Sí" else 1, format_func=td,
                )
                guardar = st.form_submit_button(L("Guardar ficha", "Save record"))
            if guardar:
                try:
                    store.save_profile(principal,nombre_paciente,{
                        "edad":edad,"genero":genero,"antecedentes":antecedentes,"motivo":motivo_n,
                        "sintomas":sintomas_n,"tratamiento":tratamiento,"red_apoyo":red_apoyo},
                        expected_version=editing_profile['_version'])
                except (ValueError,PermissionError):
                    st.error(L('No se pudo guardar: revisa los datos y recarga la ficha.', 'Could not save: check the data and reload the record.'))
                else:
                    st.session_state.pop(snapshot_key, None)
                    st.success(L('Ficha actualizada.','Record updated.'))
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
            L("Filtrar por nivel", "Filter by level"), list(NIVELES)+["Sin evaluar"], default=list(NIVELES)+["Sin evaluar"],
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
            "Las solicitudes registradas se consultan aquí; usa Triaje para tomarlas y revisarlas.",
            "Recorded requests appear here; use Triage to take and review them.",
        ))
        if DEMO:
            st.caption(L('Ejemplos independientes: no existe integración con WhatsApp.', 'Separate examples: WhatsApp integration is not implemented.'))
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
            conteo = df.groupby("nivel").size().reindex(list(NIVELES)+["Sin evaluar"], fill_value=0).reset_index()
            conteo.columns = ["nivel", "cantidad"]
            conteo["etiqueta"] = conteo["nivel"].map(etiqueta_nivel)
            fig = px.bar(
                conteo, x="etiqueta", y="cantidad", color="nivel",
                color_discrete_map={**{k: v[3] for k, v in NIVELES.items()}, "Sin evaluar": "#8C95A5"},
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
            store.save_mood(principal, nombre_paciente, animo)
        if store.mood(principal, nombre_paciente):
            st.success(L(
                f"Gracias por compartirlo: {store.mood(principal, nombre_paciente)}. "
                "Se guarda temporalmente para este perfil; no genera una alerta.",
                f"Thanks for sharing: {store.mood(principal, nombre_paciente)}. "
                "Stored temporarily for this profile; it does not create an alert.",
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
        "Si hay peligro inmediato, contacta los servicios de emergencia locales o al equipo de salud.",
        "These general ideas do not replace professional care. Do not change medication without talking to the prescriber. "
        "For immediate danger, contact local emergency services or the care team.",
    ))
