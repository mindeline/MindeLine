# MindeLine — Ficha clínica y triaje digital

Prototipo de demostración hecho con Streamlit para mostrar una ficha clínica, el flujo de triaje A–E y vistas de trabajo para paciente, enfermería y equipo tratante.

> **Importante:** es una demo con datos sintéticos. No está preparada para guardar ni procesar datos clínicos reales, tomar decisiones médicas ni atender emergencias. El selector de perfil no autentica usuarios ni restringe el acceso.

## Iniciar la aplicación

Desde PowerShell, en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre la dirección que muestra Streamlit, normalmente <http://localhost:8501>.

Para detener el servidor, vuelve a la ventana de PowerShell y presiona `Ctrl+C`.

## Idioma / Language

Use the **Language / Idioma** selector at the top of the sidebar to switch the interface between Spanish and English. AI-generated summaries follow the selected language. Audio transcription uses the selected language as a hint; patient names and original message/transcript content remain in the language in which they were entered or spoken.

## Perfiles y accesos de demostración

En la barra lateral, el selector **“Ver la experiencia como”** permite elegir un perfil y muestra su flujo orientativo.

| Perfil | Qué representa en la demo | Funciones relacionadas |
|---|---|---|
| **Paciente** | Persona que comparte una actualización de texto o audio. | Seleccionar un paciente de prueba, completar su ficha y enviar un mensaje para procesarlo con IA. |
| **Enfermería** | Equipo que recibe y revisa solicitudes. | Consultar la bandeja de enfermería, revisar casos de ejemplo y marcar los casos demo como revisados. |
| **Equipo tratante (médico)** | Personal clínico que consulta la información para seguimiento. | Revisar fichas y alertas, consultar el historial y usar el filtro CIE-10 de ejemplo. |
| **Administrador** | No existe como perfil funcional en esta versión. | No hay panel de administración, cuentas, contraseñas ni funciones administrativas implementadas. |

### Credenciales

No hay nombres de usuario, contraseñas ni cuentas de paciente, médico o administrador. El selector cambia el texto del flujo de demostración, pero **no oculta pestañas ni controla permisos**. Cualquier persona que pueda abrir la aplicación puede ver sus vistas.

La **Groq API Key** del panel lateral solo permite solicitar el análisis de texto/audio a Groq; no es una credencial de acceso a MindeLine. No escribas claves en este archivo ni las compartas. El análisis requiere conexión a Internet y una clave válida.

## Qué hace cada sección

- **Dashboard:** muestra el recuento de alertas, casos A/B y pendientes, además del último caso y el nivel de riesgo del paciente seleccionado.
- **Ficha clínica:** presenta y permite editar datos demo: edad, género, antecedentes, motivo de consulta, síntomas, tratamiento y red de apoyo. El resumen se genera con los campos de esa ficha.
- **Triaje clínico:** lista las alertas procesadas; permite tomar casos pendientes y muestra un aviso de crisis para nivel A.
- **Enfermería:** presenta casos sintéticos de ejemplo y ofrece marcar esos casos como revisados. Los registros del simulador aparecen en una lista resumida.
- **Equipo tratante:** ofrece filtros CIE-10 y recuentos de ejemplo. No consulta expedientes ni datos reales y no realiza diagnósticos.
- **Evolución:** muestra el historial disponible y un gráfico por nivel de riesgo del paciente seleccionado.
- **Simulador de mensajes:** procesa texto o archivos de audio mediante Groq. Se necesita una API Key válida.

### Niveles de riesgo de la demo

| Nivel | Etiqueta |
|---|---|
| A | Emergencia |
| B | Urgencia |
| C | Prioritario |
| D | Seguimiento |
| E | Rutina |

La clasificación automática es orientativa y no sustituye evaluación profesional. Ante una emergencia real, contacta los servicios de emergencia locales o un profesional de salud.

## Almacenamiento y privacidad

- No se utiliza una base de datos: las alertas se guardan en memoria mientras el proceso está activo.
- Los datos en memoria pueden desaparecer al reiniciar la aplicación.
- Hay perfiles y casos precargados ficticios para la demostración.
- No ingreses datos personales, identificadores, notas clínicas reales ni información sensible en la app o en servicios de IA externos.
- La clave de Groq no debe agregarse al código ni al README.

## Archivos principales

- `app.py`: interfaz Streamlit, perfiles demo, fichas, pestañas y flujos de trabajo.
- `db.py`: almacenamiento temporal de alertas en memoria; pese al nombre del archivo, no conecta a una base de datos.
- `backend_ai.py`: envío de texto/audio a Groq para generar transcripción y clasificación orientativa.
- `requirements.txt`: dependencias de Python.

## Pendiente antes de cualquier uso real

Implementar autenticación, permisos por rol en el servidor, almacenamiento seguro, protección de datos, auditoría, manejo seguro de secretos y revisión clínica/legal. El perfil de administrador y la autenticación paciente/médico no están disponibles en este prototipo.
