# Privacidad y consentimiento: alcance del prototipo

**Documento informativo, no asesoría jurídica ni validación clínica. Revisión para Chile al
18 de octubre de 2026.** Antes de cualquier piloto con personas o datos reales se necesita
revisión de un abogado chileno con experiencia en salud y privacidad, del responsable clínico y
del encargado institucional de seguridad/privacidad.

## Lo que esta versión permite

- Probar únicamente con cuentas, perfiles y mensajes ficticios.
- Autenticar cuentas demo configuradas localmente; cada cuenta tiene un rol y una lista de pacientes
  asignados. No hay auto-registro ni el usuario puede elevar su rol.
- Compartir las fichas y mensajes de prueba entre cuentas autorizadas del mismo proceso, en memoria.
  El proceso no ofrece persistencia, respaldo, recuperación ni un registro de consentimiento durable.
- Exigir que cada cuenta confirme la lectura de un aviso antes de entrar. La constancia de sesión
  incluye identidad, versión y hora UTC; desaparece al terminar la sesión o reiniciar el proceso.
- Enviar contenido de prueba a Groq solo tras una confirmación adicional. Revisa también la
  configuración y términos del proveedor: los datos enviados salen de esta aplicación.
- Recorrer una pantalla simulada de aceptación/rechazo al final del flujo WhatsApp antes de recibir
  un enlace. Solo se guarda temporalmente el paso y destino de navegación, no las respuestas ni una
  constancia durable de consentimiento. Aceptar no registra usuarios, ni comparte el chat.

El aviso de entrada **no es una firma electrónica, consentimiento informado clínico, autorización
legal para tratar datos personales, ni permiso para usar datos reales**. No recoge una aceptación
legalmente verificable, no prueba capacidad o representación, no administra retiros y no crea una
auditoría durable. No uses nombres, RUT, contactos, mensajes, diagnósticos, audios ni información
que permita identificar a pacientes, familiares o profesionales.

La aplicación no es un servicio de atención ni se encuentra vigilada. No uses sus etiquetas,
gráficos, recursos, alertas o respuestas de IA para diagnosticar, decidir tratamientos o priorizar
atención real. No hay garantía de detección o respuesta frente a una urgencia; contacta los canales
locales de emergencia y al equipo de salud correspondiente.

## Consentimiento de salida del bot: solo simulación

El bot de prueba muestra una elección al final del chat: aceptar y recibir el enlace elegido, o
rechazar y terminar sin enlace. El aviso describe un posible uso futuro por profesionales
autorizados y asignados, pero aclara que, en esta versión, no se guardan ni transfieren respuestas.
La sesión conserva solamente la fase y el destino durante un máximo de 30 minutos. Meta/WhatsApp
recibe y procesa los mensajes conforme a sus propias condiciones.

La aplicación web no tiene auto-registro ni formulario para solicitar acceso. Las cuentas nuevas
deben ser habilitadas por el equipo mediante la configuración existente; el bot no crea cuentas,
no vincula el número de WhatsApp con una identidad clínica y no garantiza que un profesional vea
el chat. Aceptar o rechazar en el bot es una interacción de demostración, **no consentimiento legal
para un tratamiento real de datos ni autorización para atención clínica**.

Para un servicio real, la información necesaria para decidir debe presentarse antes de solicitar
consentimiento y antes de cualquier tratamiento de datos que dependa de él. Si las respuestas se
van a conservar y compartir, falta construir y validar el registro de consentimiento, su retiro,
la asociación segura con una identidad y paciente, el registro duradero, los controles de acceso y
la transferencia al profesional asignado. No conectar esa función ni usar datos reales hasta la
revisión jurídica, clínica y de seguridad indicada abajo.

## Marco legal chileno que debe considerarse

Este resumen es una orientación inicial y no reemplaza la lectura de los textos vigentes ni el
análisis del caso concreto:

1. **Ley 19.628 sobre protección de la vida privada**, especialmente artículos 2, 4 y 10:
   define los datos sensibles, regula el tratamiento y establece reglas particulares para esos
   datos. La información sobre salud requiere protección reforzada y una base legal habilitante;
   una casilla genérica no vuelve lícito cualquier uso.
2. **Ley 20.584 sobre derechos y deberes de las personas en relación con acciones vinculadas a su
   atención en salud**, especialmente artículos 12 a 14: regula la confidencialidad y acceso a la
   ficha clínica y el consentimiento informado para acciones de atención en salud. El consentimiento
   clínico para una intervención y la autorización/base jurídica para tratar datos son asuntos
   distintos; uno no sustituye al otro.
3. **Ley 21.719**, que modifica el régimen de protección de datos personales y crea la Agencia de
   Protección de Datos Personales. Su entrada en vigencia está fijada para el **1 de diciembre de
   2026**; por tanto, a la fecha de esta revisión aún no entra en vigor, pero un proyecto que se
   pretenda usar después debe prepararse para el nuevo régimen y confirmar sus obligaciones con
   asesoría local.

Textos oficiales de la Biblioteca del Congreso Nacional:

- [Ley 19.628, texto en LeyChile](https://www.bcn.cl/leychile/navegar?idNorma=141599)
- [Ley 20.584, texto en LeyChile](https://www.bcn.cl/leychile/navegar?idNorma=1039348)
- [Ley 21.719, texto en LeyChile](https://www.bcn.cl/leychile/navegar?idNorma=1209272)

La aplicación no determina por sí sola quién es el responsable del tratamiento, qué base jurídica
corresponde, qué autorizaciones exige cada flujo, ni si una institución/proveedor cumple sus
obligaciones. Eso depende, entre otros factores, del propósito, los datos, la relación asistencial,
quién decide el uso, quién presta el servicio, los destinatarios y las transferencias involucradas.

## Información que una persona debería recibir antes de un uso real

Un flujo real debe ser específico, claro, accesible y revisado por asesoría jurídica y clínica.
Como mínimo, evaluar y comunicar:

- identidad y contacto del responsable del tratamiento y del equipo responsable de la atención;
- qué datos se recogen (incluidos identificadores, antecedentes de salud, mensajes, voz/audio,
  metadatos y datos inferidos), cuáles son opcionales y cuáles necesarios;
- propósitos concretos y base jurídica aplicable para cada propósito; evitar reutilizaciones
  incompatibles y explicar por separado atención, investigación, analítica o entrenamiento de IA;
- quién puede acceder y bajo qué necesidad y rol; qué profesionales participan; destinatarios y
  encargados externos (alojamiento, mensajería, transcripción, IA, soporte), ubicación y posibles
  transferencias internacionales;
- cuánto tiempo se conserva cada categoría, cómo se eliminan copias, audios, respaldos y registros,
  y qué excepciones legales pueden impedir el borrado;
- salvaguardas, canales para ejercer derechos, contacto para consultas/reclamos y procedimiento
  para incidentes de seguridad;
- cómo retirar una autorización cuando proceda y qué consecuencias tiene; el retiro no elimina
  automáticamente tratamientos previos ni obligaciones legales de conservación;
- funcionamiento y límites de automatizaciones/IA, revisión humana, posibilidad de error y que la
  herramienta no reemplaza atención profesional ni emergencias;
- reglas adicionales para menores de edad, personas que requieren representación, evaluación de
  capacidad y consentimiento por representante, accesibilidad e idiomas.

El acceso de un médico o enfermero no debe presumirse ilimitado por su cargo: tiene que depender de
asignaciones, propósito asistencial legítimo, mínimo acceso necesario, deber de confidencialidad,
autenticación fuerte, registro de accesos y revisión. La política debe resolver qué hacer ante
accesos indebidos, errores de asignación, solicitudes de derechos, incidentes, salida de personal
y término del servicio.

## Antes de considerar un piloto

1. Mantener el entorno actual limitado a `127.0.0.1`, usar cuentas y datos sintéticos y no compartir
   credenciales. No publicar el modo demo.
2. Designar formalmente responsables, definir finalidad/base jurídica, roles, asignaciones, aviso
   de privacidad, mecanismo de consentimiento/retirada cuando corresponda y protocolo clínico.
3. Sustituir memoria por almacenamiento cifrado y respaldado; diseñar retención/eliminación,
   auditoría protegida contra alteraciones, segregación por organización, gestión de sesiones,
   control de acceso y respuesta a incidentes.
4. Evaluar proveedores y contratos antes de transferir información; verificar localización,
   transferencias internacionales, retención, subencargados, uso para entrenamiento y borrado.
   No enviar información real a Groq ni a otro servicio desde este prototipo.
5. Configurar HTTPS, MFA, gestión segura de secretos, limitación de intentos, recuperación de
   cuentas, alertas y pruebas independientes de seguridad. Las contraseñas locales de demo no
   cubren estos requisitos.
6. Validar clínicamente cada flujo, alerta, contenido y recurso; probar accesibilidad, seguridad,
   errores y funcionamiento real de derivaciones antes de involucrar pacientes.
7. Obtener revisión escrita de asesoría jurídica chilena y del establecimiento/Comité de Ética
   cuando corresponda. La clasificación y obligaciones pueden variar según el propósito y el uso
   efectivo del software.

## Fuentes y alcance temporal

Se identificaron los textos de las tres leyes en LeyChile/BCN y se preparó este resumen como
orientación de diseño, no como dictamen jurídico. Verifica el texto consolidado, modificaciones,
reglamentos, instrucciones y criterios oficiales vigentes antes de tomar decisiones. El aviso de
la aplicación deliberadamente no afirma que se haya obtenido consentimiento legal.
