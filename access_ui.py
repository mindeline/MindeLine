"""Authentication and prototype-terms gate for the Streamlit app."""
import os
import time

import streamlit as st

from security import (
    resolve_demo_principal,
    resolve_principal,
    validate_demo_users,
)

CONSENT_VERSION = 'prototype-notice-2026-10-v1'
SESSION_SECONDS = 3600


def settings():
    try:
        return st.secrets.to_dict()
    except FileNotFoundError:
        return {}


def _text(spanish, english):
    return english if st.session_state.get('language') == 'English' else spanish


def _demo_login(users):
    st.title('MindeLine')
    st.warning(_text(
        'Acceso de prueba local. Solo datos ficticios; no uses esta app para atender pacientes.',
        'Local test access. Synthetic data only; do not use this app to treat patients.',
    ))
    with st.form('demo_login'):
        username = st.text_input(_text('Usuario', 'Username'), max_chars=64)
        password = st.text_input(
            _text('Contraseña', 'Password'), type='password', max_chars=1024
        )
        submitted = st.form_submit_button(_text('Iniciar sesión', 'Sign in'))
    if submitted:
        try:
            principal = resolve_demo_principal(username, password, users)
        except PermissionError:
            st.error(_text(
                'Usuario o contraseña incorrectos; revisa también la configuración local.',
                'Invalid username or password; also check the local account configuration.',
            ))
        else:
            st.session_state['_demo_principal'] = principal
            st.rerun()
    st.stop()


def _prototype_notice(principal):
    consent = st.session_state.get('_prototype_consent')
    if (isinstance(consent, dict)
            and consent.get('user_id') == principal.user_id
            and consent.get('version') == CONSENT_VERSION):
        return

    english = st.session_state.get('language') == 'English'
    st.title(_text('Antes de ingresar a MindeLine', 'Before entering MindeLine'))
    st.error(_text(
        'PROTOTIPO DE PRUEBA. No es un servicio clínico ni está habilitado para datos reales.',
        'TEST PROTOTYPE. This is not a clinical service and is not approved for real data.',
    ))
    st.markdown(_text(
        """
Esta demostración utiliza perfiles y cuentas ficticios. **No ingreses nombres, RUT, teléfonos,
diagnósticos, mensajes, audios ni ningún dato de salud real o que identifique a una persona.**

Los datos de prueba que ingreses quedan temporalmente en la memoria del proceso y pueden ser
visibles para las cuentas de Enfermería o Equipo tratante que estén preconfiguradas y asignadas
a ese perfil. Se pierden al reiniciar; no hay respaldo, recuperación ni un registro de consentimiento
duradero. No uses este prototipo para decisiones clínicas, tratamiento, seguimiento de pacientes ni
emergencias. No hay un equipo que vigile alertas ni garantice una respuesta.

El análisis con IA es opcional y requiere una confirmación separada. Si se habilita, el contenido
de prueba se envía al proveedor configurado. No ingreses información real aunque marques esa
confirmación.

Esta constancia acredita únicamente que la cuenta de prueba vio este aviso. **No es una firma
electrónica ni consentimiento informado legal para tratar datos personales o de salud, y no
autoriza atención clínica ni el uso de datos reales.**
        """,
        """
This demo uses synthetic accounts and profiles. **Do not enter real names, national IDs, phone
numbers, diagnoses, messages, audio, or any health information that identifies a person.**

Test data you enter stays temporarily in this process's memory and may be visible to preconfigured
Nursing or Treating Team accounts assigned to that profile. It is lost on restart; there is no
backup, recovery, or durable consent record. Do not use this prototype for clinical decisions,
treatment, patient follow-up, or emergencies. No team monitors alerts or guarantees a response.

AI analysis is optional and requires separate confirmation. If enabled, test content is sent to
the configured provider. Do not enter real information even if you check that confirmation.

This acknowledgement records only that the test account saw this notice. **It is not an
electronic signature or legally valid informed consent to process personal or health data, and
does not authorize clinical care or the use of real data.**
        """,
    ))
    if english:
        st.caption(f"Account: `{principal.user_id.removeprefix('demo:')}`")
    else:
        st.caption(f"Cuenta: `{principal.user_id.removeprefix('demo:')}`")
    with st.form('prototype_consent'):
        acknowledged = st.checkbox(_text(
            'Leí y entiendo el aviso; usaré solo datos ficticios y no usaré esta app para atención real.',
            'I read and understand this notice; I will use synthetic data only and not use this app for real care.',
        ))
        submitted = st.form_submit_button(_text(
            'Confirmar y continuar', 'Acknowledge and continue'
        ))
    if submitted:
        if not acknowledged:
            st.error(_text(
                'Debes marcar la casilla para entrar al prototipo.',
                'You must check the box to enter the prototype.',
            ))
        else:
            st.session_state['_prototype_consent'] = {
                'user_id': principal.user_id,
                'version': CONSENT_VERSION,
                'accepted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            st.rerun()
    st.stop()


def gate():
    try:
        config = settings()
    except Exception:
        st.error('No se pudo leer la configuración de acceso. / Could not read access configuration.')
        st.stop()
    mode = os.environ.get('MINDELINE_MODE', config.get('app', {}).get('mode', 'restricted'))
    if mode not in {'demo', 'restricted'}:
        st.error('Configuración de acceso inválida / Invalid access configuration.')
        st.stop()
    if st.session_state.get('_mode') not in {None, mode}:
        st.session_state.clear()
    st.session_state['_mode'] = mode

    if mode == 'demo':
        users = config.get('demo', {}).get('users')
        try:
            validate_demo_users(users)
        except PermissionError:
            st.error(
                'No hay cuentas de prueba válidas. Configura [demo].users en '
                '.streamlit/secrets.toml; consulta SEGURIDAD.md.'
            )
            st.stop()
        principal = st.session_state.get('_demo_principal')
        if principal is None:
            _demo_login(users)
    else:
        if not config.get('auth') or not config.get('access', {}).get('users'):
            st.error('Acceso restringido sin configurar. Consulta SEGURIDAD.md. / Restricted access is not configured.')
            st.stop()
        if not st.user.is_logged_in:
            st.title('MindeLine')
            if st.button('Iniciar sesión / Sign in'):
                try:
                    st.login()
                except Exception:
                    st.error('No se pudo iniciar sesión. Revisa la configuración OIDC. / Could not sign in. Check OIDC configuration.')
            st.stop()
        try:
            principal = resolve_principal(st.user.to_dict(), config['access']['users'])
        except (PermissionError, KeyError, TypeError, ValueError):
            st.error('Esta cuenta no tiene acceso. / This account is not authorized.')
            if st.button('Cerrar sesión / Sign out'):
                st.logout()
            st.stop()

    previous = st.session_state.get('_identity')
    if previous and previous != principal.user_id:
        st.session_state.clear()
    st.session_state['_identity'] = principal.user_id
    started = st.session_state.setdefault('_session_started', time.time())
    expires = st.user.get('exp') if mode == 'restricted' else None
    expired_claim = isinstance(expires, (int, float)) and time.time() >= expires
    if expired_claim or time.time() - started > SESSION_SECONDS:
        st.session_state.clear()
        if mode == 'restricted':
            st.logout()
        st.stop()

    st.sidebar.caption(_text(
        f'Cuenta: {principal.user_id.removeprefix("demo:")} · {principal.role}',
        f'Account: {principal.user_id.removeprefix("demo:")} · {principal.role}',
    ))
    if st.sidebar.button(_text('Cerrar sesión', 'Sign out')):
        st.session_state.clear()
        if mode == 'restricted':
            st.logout()
        st.stop()
    _prototype_notice(principal)
    return principal, config
