import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from urllib.parse import quote_plus
import unicodedata
from db import init_db, guardar_alerta, obtener_alertas, actualizar_estado_alerta, reiniciar_base_datos, sembrar_datos_prueba
from backend_ai import procesar_audio_o_texto, responder_chatbot, responder_chatbot_guiado

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
        "Configuración del Sistema": "System settings",
        "Groq API Key": "Groq API key",
        "Selección de Paciente": "Patient selection",
        "Paciente para la prueba": "Patient for the demo",
        "➕ Agregar Nuevo Paciente": "➕ Add new patient",
        "Nombre y Apellido del Nuevo Paciente": "New patient's full name",
        "Juan Pérez": "Juan Perez",
        "Ficha del paciente": "Patient record",
        "Simulador de Mensajes": "Message simulator",
        "Canal de Entrada": "Input method",
        "Texto Directo": "Text message",
        "Nota de Voz (Audio)": "Voice note (audio)",
        "Mensaje del Paciente": "Patient message",
        "Siento mucha angustia y dolor en el pecho, necesito ayuda.": "I feel very anxious and have chest pain. I need help.",
        "Enviar Mensaje": "Send message",
        "Procesando con Llama 3...": "Processing with Llama 3...",
        "Transcribiendo con Whisper...": "Transcribing with Whisper...",
        "🚨 Bandeja de Triaje Clínico": "🚨 Clinical Triage Inbox",
        "📈 Evolución Temporal por Paciente": "📈 Patient Risk Trends",
        "💬 Chatbot Asistencial": "💬 Support Chatbot",
        "Administración / Demo": "Admin / Demo Controls",
        "Poblar datos de prueba": "Seed demo data",
        "Limpiar Base de Datos": "Clear Database"
    },
}

CURRENT_LANGUAGE = "Español"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "mindeline_logo_transparent.png"


def tr(text, **values):
    translated = TRANSLATIONS.get(CURRENT_LANGUAGE, {}).get(text, text)
    return translated.format(**values) if values else translated


st.set_page_config(page_title="MindeLine", layout="wide", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🧠")

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

# ---------------------------------------------------------
# BARRA LATERAL: Perfiles y Configuración Backend
# ---------------------------------------------------------
st.sidebar.header(tr("🔐 Perfil de demostración"))
perfil_demo = st.sidebar.selectbox(
    tr("Ver la experiencia como"),
    ["Paciente", "Enfermería", "Equipo tratante"],
    format_func=tr,
)
st.sidebar.caption(tr("Selector de demo; no es inicio de sesión ni control de acceso."))

st.sidebar.markdown("---")
st.sidebar.header(tr("⚙️ Configuración del Sistema"))
groq_key = st.sidebar.text_input(tr("Groq API Key"), type="password", value="")

st.sidebar.markdown("---")
st.sidebar.header(tr("👤 Selección de Paciente"))
opciones_pacientes = ["María González", "Carlos Muñoz", "Ana Silva", "Pedro Morales", tr("➕ Agregar Nuevo Paciente")]
paciente_seleccionado = st.sidebar.selectbox(tr("Paciente para la prueba"), opciones_pacientes)

if paciente_seleccionado == tr("➕ Agregar Nuevo Paciente"):
    nombre_paciente = st.sidebar.text_input(tr("Nombre y Apellido del Nuevo Paciente"), tr("Juan Pérez"))
else:
    nombre_paciente = paciente_seleccionado

# ---------------------------------------------------------
# SIMULADOR DE ENTRADA (PATIENT SIMULATOR)
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header(tr("📱 Simulador de Mensajes"))
opcion_ingreso = st.sidebar.radio(tr("Canal de Entrada"), [tr("Texto Directo"), tr("Nota de Voz (Audio)")])

if opcion_ingreso == tr("Texto Directo"):
    texto_simulado = st.sidebar.text_area(
        tr("Mensaje del Paciente"), 
        tr("Siento mucha angustia y dolor en el pecho, necesito ayuda.")
    )
    if st.sidebar.button(tr("Enviar Mensaje"), use_container_width=True):
        with st.spinner(tr("Procesando con Llama 3...")):
            try:
                trans, json_res = procesar_audio_o_texto(groq_key, texto_ingresado=texto_simulado)
                guardar_alerta(
                    nombre_paciente=nombre_paciente,
                    tipo_mensaje="Texto",
                    contenido=texto_simulado,
                    transcripcion=trans,
                    nivel=json_res.get("nivel_riesgo", "E"),
                    resumen=json_res.get("resumen_clinico", "Sin resumen"),
                    phq9=json_res.get("phq9_estimado", 0)
                )
                st.sidebar.success(f"✅ Alerta registrada para {nombre_paciente}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

elif opcion_ingreso == tr("Nota de Voz (Audio)"):
    audio_file = st.sidebar.file_uploader(tr("Subir nota de voz (.mp3, .wav)"), type=["mp3", "wav", "m4a"])
    if audio_file and st.sidebar.button(tr("Procesar Audio"), use_container_width=True):
        with st.spinner(tr("Transcribiendo con Whisper...")):
            try:
                temp_path = f"temp_{audio_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(audio_file.getbuffer())
                
                trans, json_res = procesar_audio_o_texto(groq_key, audio_file_path=temp_path)
                guardar_alerta(
                    nombre_paciente=nombre_paciente,
                    tipo_mensaje="Audio",
                    contenido="[Nota de voz]",
                    transcripcion=trans,
                    nivel=json_res.get("nivel_riesgo", "E"),
                    resumen=json_res.get("resumen_clinico", "Sin resumen"),
                    phq9=json_res.get("phq9_estimado", 0)
                )
                st.sidebar.success(f"✅ Audio procesado para {nombre_paciente}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

# Controles de Administración en Sidebar
st.sidebar.markdown("---")
st.sidebar.header(tr("Administración / Demo"))
col_adm1, col_adm2 = st.sidebar.columns(2)
with col_adm1:
    if st.button("🌱 Poblar BD"):
        sembrar_datos_prueba()
        st.rerun()
with col_adm2:
    if st.button("🧹 Limpiar BD"):
        reiniciar_base_datos()
        st.rerun()

# ---------------------------------------------------------
# ENCABEZADO DE PÁGINA
# ---------------------------------------------------------
logo_col, title_col = st.columns([1, 4], vertical_alignment="center")
if LOGO_PATH.exists():
    logo_col.image(str(LOGO_PATH), width=110)

with title_col:
    st.title("🧠 MindeLine: Ficha Clínica & Triaje Digital")
    st.caption("Plataforma de Asistencia Clínica en Tiempo Real | Protocolos Algorítmicos A-E")

# ---------------------------------------------------------
# VISTAS Y PESTAÑAS
# ---------------------------------------------------------
tab_triaje, tab_analitica, tab_chatbot = st.tabs([
    tr("🚨 Bandeja de Triaje Clínico"), 
    tr("📈 Evolución Temporal por Paciente"), 
    tr("💬 Chatbot Asistencial")
])

alertas = obtener_alertas()

# 1. Pestaña de Triaje Clínico
with tab_triaje:
    if not alertas:
        st.info("👋 No hay alertas registradas aún. El sistema está listo para recibir mensajes o audio del paciente.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Interacciones Totales", len(alertas))
        m2.metric("Emergencias Nivel A", sum(1 for a in alertas if a[5] == 'A'))
        m3.metric("Urgencias Nivel B", sum(1 for a in alertas if a[5] == 'B'))
        m4.metric("Casos Pendientes", sum(1 for a in alertas if a[8] == 'Pendiente'))

        st.markdown("---")

        color_map = {
            'A': "🔴 **NIVEL A - EMERGENCIA**",
            'B': "🟠 **NIVEL B - URGENCIA**",
            'C': "🟡 **NIVEL C - PRIORITARIO**",
            'D': "🔵 **NIVEL D - SEGUIMIENTO**",
            'E': "🟢 **NIVEL E - RUTINA**"
        }

        for a in alertas:
            alerta_id, nombre, fecha, tipo, transcripcion, nivel, resumen, phq9, estado = a
            
            with st.expander(f"{color_map.get(nivel, nivel)} | Paciente: {nombre} | [{estado}] — {fecha}"):
                if nivel == 'A':
                    st.error("🚨 **PROTOCOLO DE CRISIS:** Derivar a SAMU 131 o Salud Responde *4141.")
                
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**Transcripción:** *\"{transcripcion}\"*")
                    st.write(f"**Síntesis:** {resumen}")
                    if phq9 is not None and phq9 > 0:
                        st.progress(min(phq9 / 27.0, 1.0), text=f"Estimación PHQ-9: {phq9} / 27 puntos")
                with c2:
                    st.caption(f"Tipo: **{tipo}**")
                    if estado == 'Pendiente':
                        if st.button("Tomar Caso", key=f"btn_{alerta_id}", use_container_width=True):
                            actualizar_estado_alerta(alerta_id, "En Atencion")
                            st.rerun()
                    else:
                        st.success(f"✔ {estado}")

# 2. Pestaña de Analítica
with tab_analitica:
    if alertas:
        df = pd.DataFrame(alertas, columns=["id", "nombre", "fecha", "tipo", "transcripcion", "nivel", "resumen", "phq9", "estado"])
        pacientes_unicos = df["nombre"].unique().tolist()
        
        paciente_filtro = st.selectbox("Seleccionar paciente para ver historial:", pacientes_unicos)
        df_paciente = df[df["nombre"] == paciente_filtro]
        
        nivel_num = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
        df_paciente['nivel_num'] = df_paciente['nivel'].map(nivel_num)

        fig = px.line(
            df_paciente, 
            x="fecha", 
            y="nivel_num", 
            markers=True,
            title=f"Evolución por nivel de riesgo para {paciente_filtro}",
            labels={"nivel_num": "Gravedad", "fecha": "Fecha"}
        )
        fig.update_yaxes(tickvals=[1, 2, 3, 4, 5], ticktext=['E (Rutina)', 'D (Seguimiento)', 'C (Prioritario)', 'B (Urgente)', 'A (Emergencia)'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_paciente[["fecha", "nivel", "resumen", "estado"]], use_container_width=True)
    else:
        st.info("No hay datos suficientes para graficar la evolución.")

# 3. Pestaña de Chatbot Asistencial
# ---------------------------------------------------------
# PESTAÑA CHATBOT GUIADO (OPCIONES PREDETERMINADAS)
# ---------------------------------------------------------
with tab_chatbot:
    st.subheader(f"💬 Orientación Asistida con MindeBot")
    st.caption("Selecciona una de las opciones sugeridas para recibir contención y orientación inmediata.")

    # Opciones iniciales para cuando comienza la interacción
    OPCIONES_INICIALES = [
        "Siento mucha ansiedad o angustia ahora",
        "Tengo problemas para dormir",
        "Me siento muy triste y sin energía",
        "Quiero saber cómo contactar a mi equipo de salud"
    ]

    # Inicializar el estado del chat en session_state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant", 
                "content": f"Hola {nombre_paciente}, soy MindeBot 🧠. Estoy aquí para escucharte y guiarte. ¿En qué te puedo ayudar hoy?"
            }
        ]
        st.session_state.current_options = OPCIONES_INICIALES

    # 1. Renderizar el historial de conversación en pantalla
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown("---")
    st.write("👉 **Selecciona una respuesta:**")

    # 2. Renderizar los botones de opciones predeterminadas
    cols = st.columns(len(st.session_state.current_options))
    
    opcion_elegida = None
    for idx, opcion in enumerate(st.session_state.current_options):
        # Usamos columnas o una lista vertical según la cantidad de opciones
        if st.button(opcion, key=f"opt_btn_{len(st.session_state.chat_history)}_{idx}", use_container_width=True):
            opcion_elegida = opcion

    # 3. Procesar la opción cuando el usuario hace clic en algún botón
    if opcion_elegida:
        # Registrar la elección del usuario
        st.session_state.chat_history.append({"role": "user", "content": opcion_elegida})
        
        with st.spinner("MindeBot está preparando tu orientación..."):
            if not groq_key:
                respuesta_bot = "⚠️ Por favor ingresa tu API Key de Groq en la barra lateral para continuar la interacción."
                nuevas_opciones = OPCIONES_INICIALES
            else:
                data_bot = responder_chatbot_guiado(groq_key, opcion_elegida)
                respuesta_bot = data_bot.get("respuesta", "Entiendo, sigamos conversando.")
                nuevas_opciones = data_bot.get("siguientes_opciones", OPCIONES_INICIALES)

            # Registrar la respuesta del bot y actualizar las siguientes opciones
            st.session_state.chat_history.append({"role": "assistant", "content": respuesta_bot})
            st.session_state.current_options = nuevas_opciones
            
        st.rerun()

    # Botón discreto para reiniciar la conversación
    if st.button("🔄 Reiniciar conversación", help="Vuelve al saludo inicial"):
        st.session_state.chat_history = [
            {
                "role": "assistant", 
                "content": f"Hola {nombre_paciente}, soy MindeBot 🧠. Estoy aquí para escucharte y guiarte. ¿En qué te puedo ayudar hoy?"
            }
        ]
        st.session_state.current_options = OPCIONES_INICIALES
        st.rerun()
    st.subheader(f"💬 Conversación de Orientación en Vivo con {nombre_paciente}")
    st.caption("Espacio interactivo de contención inicial asistido por IA.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Hola, soy MindeBot. Estoy aquí para escucharte y apoyarte. ¿Cómo te has sentido hoy, {nombre_paciente}?"}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("MindeBot está respondiendo..."):
                respuesta = responder_chatbot(groq_key, st.session_state.messages)
                st.markdown(respuesta)
        
        st.session_state.messages.append({"role": "assistant", "content": respuesta})