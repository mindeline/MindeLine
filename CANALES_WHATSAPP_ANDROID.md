# WhatsApp → MindeLine web o Android

## Estado de esta entrega

Se preparó el código del bot de acceso y un proyecto Android basado en la web existente.
**Todavía no hay una APK compilada ni un bot conectado a WhatsApp.**
Faltan la URL real de la web, un dominio público para el servicio de enlaces/webhook,
configuración de Meta y la compilación/firma de Android. El entorno de esta entrega no dispone
del SDK Android ni Gradle; no se ha validado el proyecto en un dispositivo.

La web MindeLine reforzada sigue incluida. El bot utiliza WhatsApp Cloud API de Meta como
implementación inicial; si el número usa otro proveedor, hay que adaptar el conector.
La ruta `/demo` sí permite recorrer una simulación local del chat y abrir la web local; no envía mensajes
ni representa una conexión real con WhatsApp.

## Recorrido previsto

1. La persona escribe al número del bot; el bot pregunta cómo se siente y ofrece opciones con emojis.
2. Después pregunta si tomó su medicación, si podrá asistir a su próxima cita y si quiere hablar con enfermería.
3. Al terminar, la persona elige **Abrir web** o **Abrir app Android**.
4. Antes de enviar el enlace, el bot muestra una simulación de consentimiento y ofrece aceptar o rechazar.
5. Si acepta, recibe el enlace web o `https://DOMINIO-DE-ACCESO/open`; si rechaza, termina el flujo sin enviar enlace.
6. La página informa que las cuentas nuevas deben solicitarse al equipo, que revisa y habilita el acceso.
7. Si la app está instalada y el dominio verificado, Android puede abrirla directamente; si no, se muestran las opciones disponibles.

Los enlaces no contienen nombre, teléfono, datos clínicos ni tokens de sesión.
El bot no procesa audios, no analiza respuestas ni calcula prioridad. Las respuestas no se guardan ni se
envían a MindeLine; el servicio conserva en memoria solo el paso actual y destino elegido durante un máximo
de 30 minutos para poder mostrar la pregunta siguiente. La elección de aceptar/rechazar tampoco se registra
como consentimiento durable. El aviso indica que, en un servicio real, los datos de salud podrían ser
consultados por profesionales autorizados y asignados; **en este prototipo, aceptar solo simula esa decisión:
no crea una cuenta, no conserva ni comparte las respuestas y no es consentimiento informado ni firma legal**.
La web actual no tiene formulario de registro automático; una cuenta nueva debe ser habilitada por el equipo.
WhatsApp/Meta procesa los mensajes según sus propias condiciones. Si recibe audio, indica que se responda
por escrito; no lo descarga, escucha ni transcribe. La encuesta es un prototipo, no una evaluación ni una
recomendación clínica.
La aplicación Android reutiliza la experiencia web alojada y necesita Internet.
No aporta una base de datos ni acceso offline.

## Probar el servicio local sin WhatsApp

Desde la raíz de MindeLine, si Streamlit ya está funcionando en `127.0.0.1:8502`:

```powershell
$env:CHANNEL_MODE = "preview"
$env:MINDELINE_DEMO_WEB_URL = "http://127.0.0.1:8502"
python -m uvicorn channels.server:app --host 127.0.0.1 --port 8080 --no-access-log
```

Abre http://localhost:8080/demo y recorre **Enviar Hola → emoji → 3 preguntas → web/app → aceptar o rechazar**.
Esto solo simula el intercambio del bot en el navegador y termina en la demo Streamlit. La URL de
demostración solo acepta loopback en modo preview; no guarda las respuestas, no habilita el webhook
ni envía nada a Meta.
Para usar el servidor de canales por primera vez, instala `channels/requirements.txt`.

## Conectar WhatsApp más adelante

El archivo `channels/.env.example` enumera las variables necesarias. Es una plantilla y no se
carga automáticamente: configúralas en el entorno del servidor o el gestor de secretos del host.

| Variable | Uso |
|---|---|
| `CHANNEL_MODE` | `preview` por defecto; `live` exige configuración completa. |
| `MINDELINE_WEB_URL` | URL HTTPS de la web de MindeLine, sin datos personales en query strings. |
| `MINDELINE_DEMO_WEB_URL` | Enlace de loopback usado solo por la simulación local en `preview`; no se acepta en modo live. |
| `MINDELINE_GATEWAY_URL` | Origen HTTPS del servicio de acceso, sin ruta. |
| `MINDELINE_APK_URL` | URL HTTPS del APK firmado; opcional mientras no esté disponible. |
| `WHATSAPP_VERIFY_TOKEN` | Token aleatorio de al menos 24 caracteres para verificar el webhook. |
| `META_APP_SECRET` | Secreto de la aplicación Meta para validar firmas. |
| `WHATSAPP_ACCESS_TOKEN` | Token autorizado para el número del bot. |
| `WHATSAPP_PHONE_NUMBER_ID` | Identificador del número dentro de la API, no su teléfono visible. |
| `META_GRAPH_VERSION` | Versión compatible seleccionada en la aplicación Meta, por ejemplo formato `vNN.0`. No hay versión supuesta. |
| `ANDROID_SHA256` | Huella del certificado que firma la APK instalada, en formato AA:BB:… |

Configura en Meta el callback `https://DOMINIO-DE-ACCESO/webhook` y suscribe el campo `messages`.
El endpoint GET verifica el token; POST valida `X-Hub-Signature-256` contra el cuerpo original.
Los eventos de otro número y mensajes de más de 23 horas se descartan. El bot solo responde
al remitente del evento autenticado; no inicia campañas ni envíos a listas.
No se han usado números, credenciales ni envíos reales en esta entrega.

Para pruebas usa el número/cuentas de prueba de tu configuración Meta. El uso de un número real,
permisos, disponibilidad y límites dependen de la configuración vigente de tu cuenta.

## Seguridad y límites del bot

- Guardar tokens y secretos solo en el servidor; nunca en Android o frontend.
- Desplegar con HTTPS. Mantener desactivados los access logs que puedan registrar el token de verificación
  en la query del webhook, también en el proxy. No registrar cuerpos, teléfonos ni headers de autorización.
- Un solo worker/proceso: los hashes de IDs de mensajes recibidos se deduplican durante 24 horas en memoria,
  con máximo 5.000 entradas. No se conservan los textos entrantes ni teléfonos en esa estructura.
- El endpoint espera la respuesta de Meta antes de confirmar la recepción. Es un prototipo de bajo volumen,
  no una cola durable. Bajo carga el tiempo de respuesta puede causar reintentos de Meta.
- Un timeout tras un envío que Meta sí aceptó puede producir una respuesta duplicada al reintentar.
  Reiniciar también pierde la deduplicación. Una versión de producción necesita cola/outbox durable,
  control de abuso y supervisión operativa.
- No hay vínculo automático teléfono↔paciente. El acceso clínico se decide en la web con OIDC y permisos.
- El bot no entrega atención ni activa un protocolo de emergencias.

## Preparar Android

El proyecto `android/` usa Android Browser Helper: TWA cuando el dominio está verificado y Custom Tabs
con barra del navegador cuando no lo está. No usa un WebView propio para introducir credenciales.
No reenvía URLs ni extras entrantes: abre exclusivamente la URL configurada.

Cuando conozcas las URLs reales, desde la raíz:

```powershell
python channels/configure_android.py --web-url "https://TU-WEB" --gateway-url "https://TU-DOMINIO-DE-ACCESO"
```

Esto genera `android/mindeline.properties` y las declaraciones de dominios. No almacena secretos.
El proyecto bloquea la compilación si no se configura una URL real.

Requisitos de compilación: Android SDK API 36, JDK 17, Gradle 8.13, Android Gradle Plugin 8.13.2.
Dependencia Android Browser Helper fijada a 2.7.4. La configuración está preparada, pero no compilada aquí.

1. Instala Android Studio y los componentes indicados. Abre la carpeta `android`.
2. Configura Gradle 8.13 local en Android Studio o instálalo en PATH. No se incluye un Gradle Wrapper binario.
3. Con Gradle disponible, ejecuta dentro de `android`: `gradle assembleDebug`.
4. La salida esperada es `app/build/outputs/apk/debug/app-debug.apk`.
5. Prueba login, navegación, subida de audio, cambio de idioma, cierre de sesión y enlaces en un Android real.
6. Para distribuir, genera una APK firmada desde Android Studio, conserva la clave de firma bajo tu control
   y publica su enlace en `MINDELINE_APK_URL`. No incluyas el keystore en el repositorio.

Una APK debug es para pruebas. Publicar en Google Play requiere un proceso de lanzamiento y revisión separado.

## Asociar enlaces y aplicación

El servicio sirve `/.well-known/assetlinks.json` cuando `ANDROID_SHA256` está configurado.
La huella debe ser la del certificado de la APK instalada; debug, firma propia y Play App Signing pueden diferir.

Para que `/open` abra la app, sirve el archivo desde el dominio de acceso y verifica Android App Links.
Para mostrar la web sin barra del navegador, publica la asociación también en el dominio real de la web.
**Si tu hosting no permite servir `/.well-known/assetlinks.json` en la raíz del dominio, esa verificación
puede no ser posible allí.** En ese caso se usa Custom Tabs o se prepara un dominio propio con el hosting adecuado.
No se desactiva la verificación de dominios para aparentar que funciona.

## Pruebas y fuentes

`python -m pytest tests channels/tests -q`

El bot se prueba con HTTP local y remitentes simulados: firma, verificación, flujo de ánimo y tres
preguntas, botones de salida, duplicados, fallos de envío, modo preview, URLs y generación Android.
No hay pruebas end-to-end con WhatsApp ni compilación/prueba en un Android.

Fuentes oficiales consultadas:
- https://www.postman.com/meta/whatsapp-business-platform/request/x0kd1at/send-reply-button
- https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/
- https://developer.android.com/training/app-links
- https://developer.chrome.com/docs/android/trusted-web-activity/integration-guide
- https://github.com/GoogleChrome/android-browser-helper/blob/main/README.md
- https://developer.android.com/build/releases/agp-8-13-0-release-notes
