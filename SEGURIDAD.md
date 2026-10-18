# Seguridad y límites de esta revisión

## Alcance

Revisión de ingeniería sobre una demo sintética. No constituye una certificación, auditoría
independiente ni autorización para procesar datos clínicos reales. Añadir login no resuelve
persistencia, consentimiento clínico, retención, validación de triage o protocolos de atención.

## Dos modos sin mezcla de datos

- **demo**: debe habilitarse explícitamente con `MINDELINE_MODE=demo`; usa cuentas locales
  preconfiguradas con contraseñas PBKDF2, roles y pacientes asignados en `secrets.toml`.
  No hay registro abierto ni selección de rol por el usuario. Solo ejecución local y datos sintéticos.
- **restricted**: valor predeterminado. OIDC identifica a la persona; una lista del servidor decide
  su rol y pacientes permitidos. Configuración ausente o inválida bloquea el acceso.
  Comparte un repositorio temporal entre usuarios autorizados **del mismo proceso**.

Los permisos se verifican al consultar pacientes, solicitudes, audio, historial y al modificar
fichas o casos. Ocultar pestañas es solo un complemento. No existe registro abierto.
Los hashes de contraseñas demo y las asignaciones se guardan en `.streamlit/secrets.toml`, que no
debe publicarse. PBKDF2 reduce el riesgo de exposición accidental, pero no convierte las cuentas
locales de prueba en un sistema apto para producción.

Para generar el hash de una contraseña nueva (mínimo 12 caracteres), desde la raíz del proyecto:

```powershell
python -c "from security import hash_demo_password; import getpass; print(hash_demo_password(getpass.getpass('Password (12+ characters): ')))"
```

Pega el valor resultante en `password_hash` de la cuenta correspondiente en `[[demo.users]]`.
Usa contraseñas únicas de prueba, no credenciales personales. El proceso demo no verifica correo,
no ofrece recuperación de contraseña ni limita intentos de inicio de sesión; no lo expongas a Internet.
Las contraseñas solo se usan para autenticar, no se guardan en la sesión.

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

## Aviso previo obligatorio

Antes de mostrar la interfaz, cada identidad debe confirmar que leyó el aviso del prototipo.
La constancia contiene versión, identidad y hora UTC dentro de la sesión Streamlit; se pierde al
cerrarla o reiniciar el proceso. No es una firma electrónica, consentimiento informado legal ni
un registro durable de consentimiento. En el modo OIDC se exige la misma constancia; el proveedor
de identidad sigue gestionando las credenciales.

El aviso prohíbe ingresar datos reales, explica el almacenamiento temporal compartido entre cuentas
del mismo proceso, la ausencia de vigilancia clínica y el envío opcional a Groq. La confirmación
separada de IA no sustituye la autorización para tratar datos reales. Consulta
[PRIVACIDAD_Y_CONSENTIMIENTO.md](./PRIVACIDAD_Y_CONSENTIMIENTO.md).

## Secretos y despliegue

`secrets.toml` y `.env` están excluidos de Git. El archivo de ejemplo no contiene secretos.
La clave Groq se define en el servidor en modo restringido. No incluir claves en capturas, ZIPs ni commits.
Si una clave se publicó antes, retirarla del archivo no la invalida: debe rotarse en su proveedor.

La configuración incluida escucha solo en localhost y mantiene CORS/XSRF habilitados.
Para un entorno remoto, usar HTTPS y acceso restringido, configurar correctamente el proxy y la
URI OIDC, y revisar la infraestructura. No se incluye un despliegue público automatizado.

## Datos y auditoría

Todo vive en RAM. Se pierde al reiniciar y no se comparte entre varios procesos/réplicas.
Las identidades demo autorizadas de un mismo proceso comparten el repositorio; una cuenta Paciente
solo accede a su asignación y los roles profesionales a las asignaciones configuradas. No usar
múltiples workers como si compartieran una base de datos. El límite de 1.000 solicitudes
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
- El aviso de entrada solo confirma lectura de las condiciones de la demo; no es consentimiento
  informado ni habilita tratamiento de datos personales o de pacientes.

## Siguientes pasos antes de otro nivel de uso

Persistencia y backups; IDs estables; auditoría durable; pruebas del proveedor OIDC y despliegue;
revisión clínica de criterios y recursos; controles de retención y eliminación; evaluación del
tratamiento de datos por proveedores; revisión de seguridad independiente. Mantener datos sintéticos.
