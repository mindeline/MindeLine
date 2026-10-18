from pathlib import Path
import sys
from uuid import uuid4
import pytest
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from security import hash_demo_password

DEMO_HASH=hash_demo_password('synthetic-test-password')
DEMO_USERS=[
    dict(username='patient',password_hash=DEMO_HASH,role='Paciente',patients=['María González']),
    dict(username='nurse',password_hash=DEMO_HASH,role='Enfermería',patients=['María González','Carlos Muñoz']),
    dict(username='clinician',password_hash=DEMO_HASH,role='Equipo tratante',
         patients=['María González','Carlos Muñoz','Ana Silva','Pedro Morales']),
]

def app(monkeypatch, username='patient', store_id=None):
    import access_ui
    monkeypatch.setenv('MINDELINE_MODE','demo')
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setattr(access_ui,'settings',lambda:{
        'app':{'mode':'demo','store_id':store_id or uuid4().hex},
        'demo':{'users':DEMO_USERS},
    })
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    assert not at.exception
    next(x for x in at.text_input if x.label=='Usuario').input(username)
    next(x for x in at.text_input if x.label=='Contraseña').input('synthetic-test-password')
    button(at,'Iniciar sesión').click().run()
    assert not at.exception
    assert any('PROTOTIPO DE PRUEBA' in x.value for x in at.error)
    at.checkbox[0].check()
    button(at,'Confirmar y continuar').click().run()
    assert not at.exception
    return at

def button(at,label):return next(x for x in at.button if x.label==label)
def text_area(at,label):return next(x for x in at.text_area if x.label==label)

def test_demo_patient_does_not_edit_medication(monkeypatch):
    at=app(monkeypatch)
    assert not any('Editar ficha' in e.label for e in at.expander)
    assert len(at.tabs)==4

def test_all_profiles_and_languages_render(monkeypatch):
    for username in ['nurse','clinician','patient']:
        at=app(monkeypatch,username)
        assert not any(s.key=='perfil_demo_seleccionado' for s in at.selectbox)
        at.selectbox(key='language').select('English').run()
        assert not at.exception
        at.selectbox(key='language').select('Español').run()
        assert not at.exception

def test_message_without_ai_survives_and_case_closes(monkeypatch):
    at=app(monkeypatch,store_id='shared-flow-test')
    text_area(at,'Mensaje ficticio').input('Actualización sintética para prueba')
    button(at,'Registrar actualización').click().run()
    assert not at.exception
    assert any('sin análisis válido' in w.value for w in at.warning)
    at=app(monkeypatch,'nurse','shared-flow-test')
    assert not at.exception
    button(at,'Tomar caso').click().run()
    assert not at.exception
    text_area(at,'Nota de revisión y acción realizada').input('Revisión sintética completada')
    button(at,'Cerrar como revisado').click().run()
    assert not at.exception
    assert not any(b.label=='Tomar caso' for b in at.button)
    assert not any(b.label=='Cerrar como revisado' for b in at.button)

def test_provider_failure_keeps_case(monkeypatch):
    import backend_ai
    def fail(*a,**k):raise RuntimeError('secret-key-must-not-appear')
    monkeypatch.setattr(backend_ai,'procesar_audio_o_texto',fail)
    at=app(monkeypatch,store_id='provider-failure-test')
    text_area(at,'Mensaje ficticio').input('Mensaje sintético de prueba')
    next(x for x in at.text_input if x.label=='Groq API key').input('test-key')
    at.checkbox[0].check()
    button(at,'Registrar actualización').click().run()
    assert not at.exception
    assert any('sin análisis válido' in w.value for w in at.warning)
    assert not any('secret-key' in x.value for x in at.error)
    at=app(monkeypatch,'nurse','provider-failure-test')
    assert any('Análisis fallido' in x.value for x in at.markdown)

def test_invalid_mode_blocks_everything(monkeypatch):
    monkeypatch.setenv('MINDELINE_MODE','typo')
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not at.exception
    assert at.error and not at.tabs

def test_demo_mode_fails_closed_without_local_accounts(monkeypatch):
    import access_ui
    monkeypatch.setenv('MINDELINE_MODE','demo')
    monkeypatch.setattr(access_ui,'settings',lambda:{
        'app':{'mode':'demo'},'demo':{'users':[]},
    })
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not at.exception
    assert any('No hay cuentas de prueba válidas' in e.value for e in at.error)
    assert not at.tabs

def test_prototype_notice_blocks_until_acknowledged(monkeypatch):
    import access_ui
    monkeypatch.setenv('MINDELINE_MODE','demo')
    monkeypatch.setattr(access_ui,'settings',lambda:{
        'app':{'mode':'demo','store_id':'notice-test'},'demo':{'users':DEMO_USERS},
    })
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    at.text_input[0].input('patient')
    at.text_input[1].input('synthetic-test-password')
    button(at,'Iniciar sesión').click().run()
    assert any('PROTOTIPO DE PRUEBA' in e.value for e in at.error)
    button(at,'Confirmar y continuar').click().run()
    assert any('Debes marcar la casilla' in e.value for e in at.error)
    assert not at.tabs

def test_restricted_without_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv('MINDELINE_MODE','restricted')
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not at.exception
    assert at.error and not at.tabs

@pytest.mark.parametrize('authorized',[True,False])
def test_restricted_identity_gate_with_mock_claims(monkeypatch,authorized):
    import access_ui
    class User(dict):
        is_logged_in=True
        def to_dict(self):return dict(self)
    monkeypatch.setenv('MINDELINE_MODE','restricted')
    monkeypatch.setattr(access_ui.st,'user',User(iss='https://issuer.test',sub='allowed' if authorized else 'unknown'))
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
    at.secrets['auth']={'client_id':'test'}
    at.secrets['access']={'users':[dict(issuer='https://issuer.test',subject='allowed',role='Paciente',patients=['María González'])]}
    at.run()
    assert not at.exception
    if authorized:
        assert any('PROTOTIPO DE PRUEBA' in x.value for x in at.error)
        at.checkbox[0].check()
        button(at,'Confirmar y continuar').click().run()
        assert not at.exception
        assert len(at.tabs)==4
        assert at.selectbox(key='paciente_seleccionado').options==['María González']
        assert not any(s.key=='perfil_demo_seleccionado' for s in at.selectbox)
        assert not any(e.label=='Editar ficha' for e in at.expander)
    else:
        assert at.error and not at.tabs

def test_profile_save_preserves_revision_and_changes(monkeypatch):
    at=app(monkeypatch,'clinician')
    text_area(at,'Síntomas principales').input('Cambio sintético verificado')
    button(at,'Guardar ficha').click().run()
    assert not at.exception
    assert text_area(at,'Síntomas principales').value=='Cambio sintético verificado'

def test_html_in_name_is_escaped_in_card(monkeypatch):
    at=app(monkeypatch,'nurse')
    at.selectbox(key='paciente_seleccionado').select('__nuevo__').run()
    next(x for x in at.text_input if x.label=='Nombre ficticio').input('<img src=x onerror=alert(1)>').run()
    assert not at.exception
    cards=[m.value for m in at.markdown if "<div class='ml-card" in m.value]
    assert any('&lt;img' in m for m in cards)
    assert all('<img src=x' not in m for m in cards)
