# MindeLine — prototipo de demostración

Prototipo Streamlit bilingüe para explorar fichas y revisión de solicitudes de salud mental.
**Solo cuentas y datos sintéticos. No preparado para pacientes reales, decisiones clínicas ni emergencias.**

No incluye una base de datos. Las fichas, solicitudes, auditoría y constancia de lectura son temporales.
Consulta [PRIVACIDAD_Y_CONSENTIMIENTO.md](./PRIVACIDAD_Y_CONSENTIMIENTO.md) antes de probarla.

## Inicio local: PowerShell / Windows

Desde la carpeta que contiene `app.py` (Python 3.12 recomendado):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
# Reemplaza cada hash de ejemplo por uno generado localmente (instrucciones abajo).
$env:MINDELINE_MODE = "demo"
python -m streamlit run app.py
```

En macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
MINDELINE_MODE=demo python -m streamlit run app.py
```

Genera un hash para cada usuario con `python -c "from security import hash_demo_password; import getpass; print(hash_demo_password(getpass.getpass('Password (12+ characters): ')))"`
y pégalo en su `password_hash` de `.streamlit/secrets.toml`. Define usuario, rol y pacientes ficticios
en `[[demo.users]]`; no hay alta abierta ni elección libre de rol. No reutilices contraseñas personales.
Abre http://localhost:8501. La configuración predeterminada escucha solo en `127.0.0.1`.
Las cuentas locales son solo para pruebas, no un sistema de autenticación apto para producción.
Las cuentas autorizadas del mismo proceso comparten el repositorio temporal para probar el recorrido.
No expongas el modo demo a Internet.

## Acceso restringido opcional

Sin `MINDELINE_MODE=demo`, la aplicación exige configuración de acceso y permanece bloqueada
si esta falta. Ver **SEGURIDAD.md** y `.streamlit/secrets.example.toml`.
Se usa el inicio de sesión OIDC de Streamlit y una lista de asignaciones del servidor.
Las contraseñas locales solo están disponibles en modo demo.
La conexión al proveedor OIDC debe configurarse y probarse antes de usar este modo.
Sigue siendo una demo con datos sintéticos incluso con inicio de sesión.

## Qué cambió

- Repositorio temporal común para fichas, solicitudes y seguimiento, protegido por un bloqueo de concurrencia.
- Solicitudes guardadas antes de intentar el análisis, incluso sin API key o cuando el proveedor falla.
- Estado de análisis separado del estado de atención. Los casos sin resultado se muestran como **Sin evaluar**.
- Mensaje original, transcripción, modelo, versión del prompt y frase de respaldo separados.
- Validación de valores y tipos de la respuesta de IA; sin cambio silencioso de modelo.
- Eliminado el PHQ-9 generado por IA: no se recopila un cuestionario ni se presenta un puntaje estimado.
- La prioridad abierta corresponde al nivel más alto entre alertas no cerradas; un nuevo E no borra un A pendiente.
  No representa una evaluación clínica del paciente. Casos sin análisis permanecen visibles en Triaje.
- Tomar caso asigna un responsable; solo ese responsable puede cerrarlo con una nota.
- Autorización de lecturas y escrituras por rol y paciente en el repositorio, además de controles de interfaz.
- El paciente no puede editar tratamiento ni otros campos clínicos.
- Confirmación explícita antes de enviar datos sintéticos a Groq, límites de entrada y de reintentos.
- Nombres y resúmenes interpolados en tarjetas HTML se escapan.
- Audio temporal eliminado del disco al terminar la llamada; los bytes se descartan al completar o cerrar el caso.
- Estados de ánimo asociados al paciente, no a una clave global de interfaz.

## Recorrido verificable sin proveedor de IA

1. Inicia sesión con una cuenta demo asignada al rol Paciente y acepta el aviso.
2. Envía un mensaje sin clave de Groq: queda registrado sin análisis.
3. Cierra sesión e inicia con una cuenta demo de Enfermería.
4. Abre Triaje, toma el caso y escribe una nota de revisión.
5. Consulta su historial de acciones.

Los roles y las asignaciones los configura el administrador local. Reiniciar el proceso pierde
todos los datos. No existe mecanismo de recuperación ni exportación de información clínica.

## IA opcional

En demo puede ingresarse una clave en el panel lateral; permanece en el estado de la sesión.
En modo restringido la clave se configura únicamente en el servidor, mediante `GROQ_API_KEY`
o `[groq].api_key` en secrets.toml. No se imprime la clave ni los errores crudos del proveedor.
El modelo se configura en `[groq].model` o `MINDELINE_AI_MODEL`; por defecto se usa
`openai/gpt-oss-20b`, cuya disponibilidad debe comprobarse en la cuenta.

El envío al proveedor requiere marcar la confirmación de datos ficticios. Esa autorización
queda asociada a la solicitud: no se puede reintentar el análisis de una solicitud no autorizada.
Para autorizar un mensaje registrado sin ella, envíalo de nuevo marcando la confirmación.
Los reintentos desde Triaje requieren clave del servidor/sesión, autorización previa,
15 segundos entre inicios de análisis por identidad y un máximo de 5 intentos por caso.

Límites: 8.000 caracteres; 5 MiB por audio; 1.000 solicitudes; 25 MiB de audio pendiente por
repositorio. Al llegar a capacidad se rechaza el envío explícitamente; no se borran casos silenciosamente.
Estas cuotas son controles básicos de demo, no protección completa contra abuso en Internet.

## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Las pruebas no requieren claves ni llaman al proveedor. Cubren permisos, aislamiento, validación,
concurrencia, errores, prioridades abiertas y recorrido de interfaz con `AppTest`.
`python test_groq.py` es un diagnóstico manual opcional que lista modelos disponibles;
no ejecuta inferencias y no se ejecuta al importar el módulo.

## Estructura

- `app.py`: interfaz, traducciones, datos sintéticos y composición del flujo.
- `db.py`: repositorio **en memoria**, sin conexión a una base de datos.
- `backend_ai.py`: validación y llamadas acotadas a Groq.
- `security.py`: identidad y permisos independientes de la interfaz.
- `access_ui.py`: puerta de entrada de contraseña local para demo, OIDC restringido y aviso obligatorio.
- `.streamlit/config.toml`: tema, escucha local, CORS/XSRF y tamaño de subida.
- `SEGURIDAD.md`: configuración, límites y comprobaciones antes de compartir la app.
- `PRIVACIDAD_Y_CONSENTIMIENTO.md`: resumen informativo del marco chileno y límites del aviso demo.
- `tests/`: pruebas automatizadas sin servicios externos.

## Funciones que siguen siendo ejemplos o están pendientes

Los recuentos CIE-10 y casos precargados de enfermería son ejemplos independientes; no hay
integración WhatsApp. Los enlaces educativos abren búsquedas en YouTube, no un catálogo revisado.
El gráfico cuenta alertas por nivel, no mide evolución clínica. No hay envío de notificaciones,
derivación externa, alertas de emergencia ni confirmación de recepción por un equipo real.

Pendientes: persistencia, identificadores de paciente independientes del nombre, auditoría durable,
recuperación, gestión de usuarios y asignaciones, notificaciones verificables, validación clínica,
revisión de privacidad y proveedores, pruebas de despliegue y revisión de seguridad independiente.

## Acceso desde WhatsApp y proyecto Android

Se agregó `channels/` con un bot de menú para WhatsApp Cloud API, página de respaldo móvil y
verificación de enlaces Android. `android/` contiene el proyecto Android, pendiente de configurar,
compilar y firmar. No se incluye una APK instalada/compilada ni un bot conectado.
Consulta `CANALES_WHATSAPP_ANDROID.md`. La web y el dominio de acceso requieren sus URLs reales.
