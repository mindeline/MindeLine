"""OIDC entry gate; authorization is separately enforced by MemoryStore."""
import os
import time
import streamlit as st
from security import resolve_principal


def settings():
    try:
        return st.secrets.to_dict()
    except FileNotFoundError:
        return {}


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
        st.sidebar.warning('DEMO: datos ficticios, sin autenticación. / Synthetic data, no authentication.')
        return None, config
    # Fail closed: missing or malformed auth does not fall back to demo.
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
        if st.button('Cerrar sesión / Sign out'): st.logout()
        st.stop()
    # Bound each application session independently of the provider's cookie lifetime.
    previous = st.session_state.get('_identity')
    if previous and previous != principal.user_id:
        st.session_state.clear()
    st.session_state['_identity'] = principal.user_id
    started = st.session_state.setdefault('_session_started', time.time())
    expires = st.user.get('exp')
    expired_claim = isinstance(expires, (int, float)) and time.time() >= expires
    if expired_claim or time.time() - started > 3600:
        st.session_state.clear()
        st.logout()
        st.stop()
    st.sidebar.caption('Acceso restringido / Restricted access')
    if st.sidebar.button('Cerrar sesión / Sign out'):
        st.session_state.clear()
        st.logout()
        st.stop()
    return principal, config
