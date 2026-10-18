# Validación de esta entrega

Revisión realizada el 18 de octubre de 2026 sobre el ZIP proporcionado.

- 44 pruebas automatizadas pasaron: `python -m pytest tests -q`.
- Sintaxis Python y archivos TOML comprobados.
- Pruebas de interfaz con Streamlit AppTest: perfiles, cambio de idioma, alta de mensaje sin IA,
  error simulado del proveedor, toma/cierre de caso, edición de ficha y escape de HTML en nombres.
- Identidad OIDC simulada: cuenta autorizada limitada a su paciente y cuenta no autorizada bloqueada.
- Permisos del repositorio, acceso cruzado, cambios de estado y responsable único bajo concurrencia.
- Validación de respuesta de IA y audio; autorización de envío, límites de reintento,
  aislamiento entre repositorios y conservación de mensajes al fallar el análisis.
- La alerta abierta A conserva prioridad frente a un resultado E posterior.

No se enviaron mensajes ni audios a Groq, ni se usaron claves reales.
No se probó un proveedor OIDC real, HTTPS/proxy, despliegue público, carga sostenida ni uso clínico.
AppTest verifica el flujo y elementos de Streamlit, no sustituye una revisión visual en todos los navegadores.
La lista de dependencias fija las versiones directas utilizadas; no es un lockfile completo
ni certifica ausencia de vulnerabilidades en las dependencias.

La entrega conserva la interfaz general y datos de ejemplo. El selector de perfiles de demo
permanece visible; en acceso restringido se reemplaza por el rol y asignaciones del servidor.
La administración de identidades y asignaciones sigue siendo configuración manual.

## Ampliación WhatsApp y Android

58 pruebas aprobadas en total (44 de la aplicación y 14 del acceso WhatsApp/enlaces).
El runner muestra un aviso de deprecación sobre el transporte HTTP del cliente de pruebas;
no hubo fallos. XML Android comprobado sintácticamente y generador de enlaces probado.
No hay APK compilada, prueba en Android, conexión Meta ni envío real de mensajes.
Se incorporaron ajustes CSS para pantallas estrechas; su aspecto en dispositivos reales sigue por revisar.
