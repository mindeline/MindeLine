import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from security import (
    Principal, hash_demo_password, resolve_demo_principal, resolve_principal,
)
from db import MemoryStore
from backend_ai import validate_result, validate_audio

PROFILE=dict(edad=30,genero='Femenino',antecedentes='',motivo='',sintomas='',tratamiento='',red_apoyo='Sí')
@pytest.fixture
def store(): return MemoryStore({'p1':PROFILE,'p2':PROFILE})
@pytest.fixture
def patient(): return Principal('patient','Paciente',frozenset({'p1'}))
@pytest.fixture
def nurse(): return Principal('nurse','Enfermería',frozenset({'p1'}))

def submit(store,patient,text='synthetic message',allow_ai=True):
    return store.submit(patient,'p1','Texto',text,allow_ai=allow_ai)

def result(level='A'):
    return dict(nivel_riesgo=level,resumen_clinico='Synthetic summary',alerta_frase='synthetic')

@pytest.mark.parametrize('claims',[{}, {'iss':'issuer'}, {'iss':'wrong','sub':'123'}, {'iss':'issuer','sub':'other'}])
def test_identity_fail_closed(claims):
    with pytest.raises(PermissionError):
        resolve_principal(claims,[dict(issuer='issuer',subject='123',role='Paciente',patients=['p1'])])

def test_identity_bound_to_subject_not_email():
    cfg=[dict(issuer='issuer',subject='123',role='Paciente',patients=['p1'])]
    user=resolve_principal(dict(iss='issuer',sub='123',email='not-used@example.test'),cfg)
    assert user.patients==frozenset({'p1'})

def test_demo_login_uses_configured_role_and_patient_scope():
    password_hash=hash_demo_password('synthetic-test-password')
    accounts=[
        dict(username='patient.demo',password_hash=password_hash,role='Paciente',patients=['p1']),
        dict(username='nurse.demo',password_hash=password_hash,role='Enfermería',patients=['p1','p2']),
    ]
    patient_user=resolve_demo_principal('PATIENT.DEMO','synthetic-test-password',accounts)
    nurse_user=resolve_demo_principal('nurse.demo','synthetic-test-password',accounts)
    assert patient_user.role=='Paciente' and patient_user.patients==frozenset({'p1'})
    assert nurse_user.role=='Enfermería' and nurse_user.demo
    with pytest.raises(PermissionError):
        resolve_demo_principal('patient.demo','incorrect-password',accounts)
    with pytest.raises(PermissionError):
        resolve_demo_principal('unknown','synthetic-test-password',accounts)

def test_demo_login_rejects_duplicate_accounts_and_patient_role_escalation():
    password_hash=hash_demo_password('synthetic-test-password')
    account=dict(username='test.user',password_hash=password_hash,role='Paciente',patients=['p1'])
    with pytest.raises(PermissionError):
        resolve_demo_principal('test.user','synthetic-test-password',[account,account])
    with pytest.raises(PermissionError):
        resolve_demo_principal('test.user','synthetic-test-password',[
            dict(account,role='Administrador')
        ])

def test_demo_patient_cannot_add_other_patients(store,patient):
    with pytest.raises(PermissionError):
        store.add_demo_patient(patient,'p3',PROFILE)

@pytest.mark.parametrize('role,patients',[('Admin',['p1']),('Paciente',['p1','p2']),('Paciente',[]),('Enfermería','p1')])
def test_bad_access_config_denied(role,patients):
    with pytest.raises(PermissionError):
        resolve_principal(dict(iss='i',sub='s'),[dict(issuer='i',subject='s',role=role,patients=patients)])

def test_patient_cannot_read_other_patient(store,patient,nurse):
    outsider=Principal('other','Paciente',frozenset({'p2'}))
    rid=submit(store,patient)
    assert store.alerts(outsider)==[]
    with pytest.raises(PermissionError): store.get(outsider,rid)
    with pytest.raises(PermissionError): store.submit(patient,'p2','Texto','message')
    assert list(store.patients(patient))==['p1']

def test_patient_cannot_edit_clinical_fields_or_take_case(store,patient):
    rid=submit(store,patient)
    with pytest.raises(PermissionError): store.save_profile(patient,'p1',PROFILE,0)
    with pytest.raises(PermissionError): store.transition(patient,rid,'En Atencion')
    with pytest.raises(PermissionError): store.audit(patient,rid)

def test_profile_version_conflict(store,nurse):
    store.save_profile(nurse,'p1',PROFILE,0)
    with pytest.raises(ValueError): store.save_profile(nurse,'p1',PROFILE,0)

def test_failure_preserves_original_and_pending_case(store,patient):
    rid=submit(store,patient)
    store.begin_analysis(patient,rid)
    store.fail_analysis(patient,rid)
    r=store.get(patient,rid)
    assert r['contenido']=='synthetic message'
    assert r['analysis']=='failed' and r['estado']=='Pendiente'
    assert r['nivel_riesgo']=='Sin evaluar'

def test_consent_required_even_on_retry(store,patient):
    rid=submit(store,patient,allow_ai=False)
    with pytest.raises(PermissionError): store.begin_analysis(patient,rid)

def test_no_false_success_missing_case(store,nurse):
    with pytest.raises(KeyError): store.transition(nurse,'missing','En Atencion')

def test_case_has_single_owner_under_concurrency(store,patient):
    rid=submit(store,patient)
    users=[Principal(str(i),'Enfermería',frozenset({'p1'})) for i in range(10)]
    def take(user):
        try: return store.transition(user,rid,'En Atencion')
        except ValueError: return False
    with ThreadPoolExecutor(max_workers=10) as pool: assert sum(pool.map(take,users))==1

def test_close_requires_owner_and_note(store,patient,nurse):
    rid=submit(store,patient)
    store.transition(nurse,rid,'En Atencion')
    with pytest.raises(ValueError): store.transition(nurse,rid,'Revisado','')
    with pytest.raises(PermissionError):
        store.transition(Principal('other','Enfermería',frozenset({'p1'})),rid,'Revisado','reviewed')
    store.transition(nurse,rid,'Revisado','Reviewed synthetic case')
    assert store.get(nurse,rid)['responsable']=='nurse'
    assert [x['action'] for x in store.audit(nurse,rid)]==['message_received','En Atencion','Revisado']

def test_latest_routine_does_not_clear_open_emergency(store,patient,nurse):
    a=submit(store,patient)
    store.begin_analysis(patient,a);store.finish_analysis(patient,a,'synthetic message',result('A'))
    # Another authorized actor avoids per-actor cooldown in this independent operation.
    e=submit(store,nurse,'synthetic routine')
    store.begin_analysis(nurse,e);store.finish_analysis(nurse,e,'synthetic routine',result('E'))
    assert store.open_risk(nurse,'p1')=='A'
    store.transition(nurse,a,'En Atencion');store.transition(nurse,a,'Revisado','Reviewed and resolved')
    assert store.open_risk(nurse,'p1')=='E'

def test_duplicate_submission_does_not_duplicate_record(store,patient):
    assert submit(store,patient)==submit(store,patient)
    assert len(store.alerts(patient))==1

def test_rate_limit(store,patient):
    rid=submit(store,patient);store.begin_analysis(patient,rid);store.fail_analysis(patient,rid)
    with pytest.raises(ValueError): store.begin_analysis(patient,rid)

def test_session_stores_do_not_leak(store,patient):
    submit(store,patient)
    other=MemoryStore({'p1':PROFILE})
    assert other.alerts(patient)==[]

@pytest.mark.parametrize('value',[{},[],dict(nivel_riesgo='Z',resumen_clinico='x',alerta_frase=''),
    dict(nivel_riesgo='A',resumen_clinico='x',alerta_frase='invented'),
    dict(nivel_riesgo='B',resumen_clinico='x',alerta_frase=''),
    dict(nivel_riesgo='E',resumen_clinico=7,alerta_frase='')])
def test_invalid_ai_is_rejected(value):
    with pytest.raises(ValueError): validate_result(value,'synthetic message')

def test_no_phq_score_is_retained():
    assert 'phq9_estimado' not in validate_result(dict(result(),phq9_estimado=27),'synthetic message')

@pytest.mark.parametrize('data,suffix',[(b'not-a-wave','.wav'),(b'ID3x','.exe'),(b'','.mp3'),(b'ID3'+b'0'*(5*1024*1024),'.mp3')],ids=['bad-wave','unsupported-extension','empty-audio','oversized-audio'])
def test_invalid_audio(data,suffix):
    with pytest.raises(ValueError): validate_audio(data,suffix)

def test_audio_preserved_on_failure_and_removed_after_success(store,patient,nurse):
    rid=store.submit(patient,'p1','Audio','[Audio]',audio=b'ID3demo',suffix='.mp3',allow_ai=True)
    r=store.begin_analysis(patient,rid);assert r['audio']==b'ID3demo'
    store.fail_analysis(patient,rid)
    r=store.begin_analysis(nurse,rid);assert r['audio']==b'ID3demo'
    store.finish_analysis(nurse,rid,'synthetic message',result())
    assert store._records[rid]['audio'] is None

def test_mood_scoped_to_patient(store,patient):
    store.save_mood(patient,'p1','🙂')
    other=Principal('other','Paciente',frozenset({'p2'}))
    assert store.mood(other,'p2') is None
