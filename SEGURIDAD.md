# Seguridad y límites de esta revisión

## Alcance

Revisión de ingeniería sobre una demo sintética. No constituye una certificación, auditoría
independiente ni autorización para procesar datos clínicos reales. Añadir login no resuelve
persistencia, consentimiento clínico, retención, validación de triage o protocolos de atención.

## Dos modos sin mezcla de datos

- **demo**: debe habilitarse explícitamente con `MINDELINE_MODE=demo`; perfiles intercambiables,
  repositorio por sesión, sin autenticación. Solo ejecución local para demostración.
- **restricted**: valor predeterminado. OIDC identifica a la persona; una lista del servidor decide
  su rol y pacientes permitidos. Configuración ausente o inválida bloquea el acceso.
  Comparte un repositorio temporal entre usuarios autorizados **del mismo proceso**.

Los permisos se verifican al consultar pacientes, solicitudes, audio, historial y al modificar
fichas o casos. Ocultar pestañas es solo un complemento. No existen administradores ni registro abierto.
En demo, el selector puede cambiar voluntariamente de identidad: nunca es una barrera de seguridad.

## Configuración OIDC

1. Registra una aplicación en un proveedor compatible con OpenID Connect, por ejemplo el proveedor
   de identidad de tu organización. Configura la URI de retorno `/oauth2callback`.
2. Copia `.streamlit/secrets.example.toml` a `.streamlit/secrets.toml`.
3. Reemplaza todos los placeholders de `[auth]` por la configuración de ese proveedor.
   Genera `cookie_secret` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
4. En `[[access.users]]` declara el **issuer + subject** exactos de las identidades autorizadas.
   No se permite elegir el rol desde el navegador ni se decide el acceso por correo electrónico.
   Obtén estos identificadores mediante la administración del proveedor, sin publicar tokens.
5. Roles permitidos: `Paciente`, `Enfermería`, `Equipo tratante`.
   Un paciente debe tener exactamente un perfil asignado. Los profesionales solo acceden a los
   perfiles listados. En esta demo las claves son los nombres exactos de `PACIENTES_INICIALES`.
6. Si activaste demo, elimina la variable antes de usar acceso restringido:
   PowerShell: `Remove-Item Env:MINDELINE_MODE -ErrorAction SilentlyContinue`.
   Bash: `unset MINDELINE_MODE`.
7. Inicia desde la carpeta raíz con `python -m streamlit run app.py`.
8. Verifica con cuentas distintas: cuenta sin permiso bloqueada, paciente sin edición clínica,
   profesional limitado a sus asignaciones y cierre exclusivo por el responsable del caso.

La autenticación usa `st.login`, `st.user` y `st.logout`; requiere `streamlit[auth]`.
Documentación: https://docs.streamlit.io/develop/api-reference/user/st.login
La app limita cada sesión a una hora y comprueba `exp` cuando el proveedor lo entrega.
Cerrar sesión elimina la sesión de la app; no garantiza cerrar la sesión del proveedor.
El proveedor puede volver a autenticar sin pedir contraseña, según su propia política.
Configura MFA y política de reautenticación en el proveedor si el entorno lo requiere.
No se han realizado pruebas con un proveedor OIDC real ni con un despliegue HTTPS en esta revisión.

## Secretos y despliegue

`secrets.toml` y `.env` están excluidos de Git. El archivo de ejemplo no contiene secretos.
La clave Groq se define en el servidor en modo restringido. No incluir claves en capturas, ZIPs ni commits.
Si una clave se publicó antes, retirarla del archivo no la invalida: debe rotarse en su proveedor.

La configuración incluida escucha solo en localhost y mantiene CORS/XSRF habilitados.
Para un entorno remoto, usar HTTPS y acceso restringido, configurar correctamente el proxy y la
URI OIDC, y revisar la infraestructura. No se incluye un despliegue público automatizado.

## Datos y auditoría

Todo vive en RAM. Se pierde al reiniciar y no se comparte entre varios procesos/réplicas.
No usar múltiples workers como si compartieran una base de datos. El límite de 1.000 solicitudes
rechaza nuevos registros, sin evicción silenciosa. El historial conserva como máximo 5.000 eventos
por repositorio y no es inmutable ni durable. No reemplaza un registro de auditoría clínico.

El mensaje original se registra antes de invocar IA. Un error deja el caso pendiente de revisión.
Los audios fallidos/no procesados siguen en memoria para revisión/reintento hasta cerrar el caso,
perder la sesión demo o reiniciar. No se ofrece reproducción. Los temporales de disco se borran
con `finally` en operación normal; una terminación abrupta puede impedir esa limpieza. La carpeta
 temporal del host debe estar protegida y sujeta a limpieza del sistema. No se promete borrado seguro.

## IA y flujo de revisión

- Se valida el JSON, tipos, longitud, nivel A–E y presencia literal de la frase de respaldo.
- Se registra el modelo configurado y la versión del prompt; no hay cambio silencioso de modelo.
- La presencia literal de una frase **no valida** la interpretación ni elimina prompt injection.
- No hay PHQ-9 inferido ni medición clínica de precisión; las etiquetas son criterios de demostración.
- Los fallos no se convierten en E ni desaparecen de la bandeja.
- La prioridad abierta no se reduce mientras permanezca abierta una alerta de mayor prioridad.
- Cerrar exige responsable y nota, pero no valida que se haya realizado atención clínica.
- No se envían SMS, emails, WhatsApp ni alertas externas; un aviso visual no equivale a notificación.
- El consentimiento incluido solo confirma datos ficticios y envío al proveedor; no es un flujo
  de consentimiento informado para datos de pacientes.

## Siguientes pasos antes de otro nivel de uso

Persistencia y backups; IDs estables; auditoría durable; pruebas del proveedor OIDC y despliegue;
revisión clínica de criterios y recursos; controles de retención y eliminación; evaluación del
tratamiento de datos por proveedores; revisión de seguridad independiente. Mantener datos sintéticos.
