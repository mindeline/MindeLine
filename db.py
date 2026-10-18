"""Thread-safe, bounded, volatile repository. NOT a database or durable audit log."""
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
import hashlib
import time

MAX_RECORDS = 1000
MAX_AUDIO_BYTES = 25 * 1024 * 1024
LEVELS = 'ABCDE'

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class MemoryStore:
    def __init__(self, patients):
        self._lock = RLock()
        self._patients = deepcopy(patients)
        for p in self._patients.values():
            p['_version'] = 0
        self._records = {}
        self._audit = []
        self._moods = {}
        self._analysis_ticks = {}

    def _event(self, actor, action, patient, record_id=None):
        self._audit.append(dict(at=utcnow(), actor=actor.user_id, action=action,
                                patient=patient, record_id=record_id))
        self._audit = self._audit[-5000:]

    def patients(self, actor):
        with self._lock:
            return {k: deepcopy(v) for k, v in self._patients.items() if k in actor.patients}

    def add_demo_patient(self, actor, name, profile):
        if not actor.demo or not name.strip() or len(name) > 100:
            raise PermissionError('Demo-only operation')
        with self._lock:
            if len(self._patients) >= 100:
                raise ValueError('Patient limit reached')
            self._patients.setdefault(name, dict(deepcopy(profile), _version=0))

    def save_profile(self, actor, patient, profile, expected_version):
        actor.authorize(patient, clinical=True)
        with self._lock:
            old = self._patients[patient]
            if expected_version != old['_version']:
                raise ValueError('Record changed. Reload before saving.')
            fields = {'edad', 'genero', 'antecedentes', 'motivo', 'sintomas', 'tratamiento', 'red_apoyo'}
            if set(profile) != fields:
                raise ValueError('Invalid profile fields')
            if type(profile['edad']) is not int or not 0 <= profile['edad'] <= 120:
                raise ValueError('Invalid age')
            if any(not isinstance(profile[k], str) or len(profile[k]) > 8000 for k in fields - {'edad'}):
                raise ValueError('Invalid profile text')
            if profile['red_apoyo'] not in {'Sí', 'No'} or profile['genero'] not in {'Femenino','Masculino','No binario','Prefiero no decirlo'}:
                raise ValueError('Invalid profile choice')
            old.update(deepcopy(profile))
            old['_version'] += 1
            old['ultima_revision'] = utcnow()
            self._event(actor, 'profile_updated', patient)

    def submit(self, actor, patient, kind, content, *, audio=None, suffix=None, allow_ai=False):
        actor.authorize(patient)
        if kind not in {'Texto', 'Audio'} or not isinstance(content, str) or len(content) > 8000:
            raise ValueError('Invalid message')
        if kind == 'Texto' and not content.strip():
            raise ValueError('Empty message')
        if kind == 'Audio':
            from backend_ai import validate_audio
            validate_audio(audio, suffix)
        digest = hashlib.sha256((patient + kind + content + str(bool(allow_ai))).encode() + (audio or b'')).hexdigest()
        with self._lock:
            # Suppress double-clicks and repeated reruns for the same sender and payload.
            for r in self._records.values():
                if r['actor'] == actor.user_id and r['digest'] == digest and time.monotonic()-r['created_tick'] < 30:
                    return r['id']
            if len(self._records) >= MAX_RECORDS:
                raise ValueError('Memory capacity reached')
            if sum(len(r.get('audio') or b'') for r in self._records.values()) + len(audio or b'') > MAX_AUDIO_BYTES:
                raise ValueError('Audio capacity reached')
            rid = uuid4().hex
            self._records[rid] = dict(id=rid, nombre_paciente=patient, fecha=utcnow(),
                tipo_mensaje=kind, contenido=content, transcripcion=content if kind=='Texto' else '',
                nivel_riesgo='Sin evaluar', resumen_clinico='', estado='Pendiente',
                analysis='pending', error=None, model=None, prompt_version=None, alerta_frase='',
                actor=actor.user_id, allow_ai=bool(allow_ai), attempts=0, responsable=None, note='', audio=audio, suffix=suffix,
                digest=digest, created_tick=time.monotonic())
            self._event(actor, 'message_received', patient, rid)
            return rid

    def _get(self, actor, rid, clinical=False):
        if rid not in self._records:
            raise KeyError('Case not found')
        r = self._records[rid]
        actor.authorize(r['nombre_paciente'], clinical=clinical)
        return r

    def get(self, actor, rid):
        with self._lock:
            r = deepcopy(self._get(actor, rid))
            # Audio is available only to the analysis path, not general views.
            for key in ('audio','digest','created_tick'): r.pop(key, None)
            return r

    def begin_analysis(self, actor, rid):
        with self._lock:
            r = self._get(actor, rid)
            if not r['allow_ai']: raise PermissionError('External analysis not authorized')
            if r['attempts'] >= 5 or time.monotonic() - self._analysis_ticks.get(actor.user_id, -100) < 15:
                raise ValueError('Analysis rate limit reached; wait before retrying')
            if r['estado'] == 'Revisado' or r['analysis'] not in {'pending','failed'}:
                raise ValueError('Analysis is not available for this case')
            r['attempts'] += 1
            self._analysis_ticks[actor.user_id] = time.monotonic()
            r['analysis'] = 'processing'
            r['error'] = None
            self._event(actor, 'analysis_started', r['nombre_paciente'], rid)
            return deepcopy(r)

    def finish_analysis(self, actor, rid, transcript, result):
        from backend_ai import validate_result
        valid = validate_result(result, transcript)
        with self._lock:
            r = self._get(actor, rid)
            if r['analysis'] != 'processing': raise ValueError('Invalid analysis state')
            r.update(valid, transcripcion=transcript, analysis='complete', error=None, audio=None)
            self._event(actor, 'analysis_completed', r['nombre_paciente'], rid)

    def fail_analysis(self, actor, rid):
        with self._lock:
            r = self._get(actor, rid)
            if r['analysis'] != 'processing': raise ValueError('Invalid analysis state')
            r.update(analysis='failed', error='analysis_unavailable')
            self._event(actor, 'analysis_failed', r['nombre_paciente'], rid)

    def transition(self, actor, rid, state, note=''):
        with self._lock:
            r = self._get(actor, rid, clinical=True)
            if state == 'En Atencion' and r['estado'] == 'Pendiente':
                r['responsable'] = actor.user_id
            elif state == 'Revisado' and r['estado'] == 'En Atencion':
                if r['responsable'] != actor.user_id: raise PermissionError('Assigned reviewer required')
                if r['analysis'] == 'processing': raise ValueError('Wait for analysis to finish')
                if not isinstance(note, str) or not 3 <= len(note.strip()) <= 2000:
                    raise ValueError('A review note is required')
                r['note'] = note.strip()
                r['audio'] = None
            else:
                raise ValueError('Invalid transition')
            r['estado'] = state
            self._event(actor, state, r['nombre_paciente'], rid)
            return True

    def alerts(self, actor):
        with self._lock:
            return [(r['id'],r['nombre_paciente'],r['fecha'],r['tipo_mensaje'],r['transcripcion'],
                r['nivel_riesgo'],r['resumen_clinico'],None,r['estado'])
                for r in reversed(list(self._records.values())) if r['nombre_paciente'] in actor.patients]

    def open_risk(self, actor, patient):
        actor.authorize(patient)
        with self._lock:
            open_records=[r for r in self._records.values() if r['nombre_paciente']==patient and r['estado']!='Revisado']
            levels=[r['nivel_riesgo'] for r in open_records if r['nivel_riesgo'] in LEVELS and len(r['nivel_riesgo'])==1]
            # Unassessed cases remain explicitly visible; never present them as routine.
            return min(levels) if levels else 'Sin evaluar'

    def save_mood(self, actor, patient, mood):
        actor.authorize(patient)
        if mood not in {'😄','🙂','😐','😟','😢'}: raise ValueError('Invalid mood')
        with self._lock:
            self._moods[patient] = mood
            self._event(actor, 'mood_updated', patient)

    def mood(self, actor, patient):
        actor.authorize(patient)
        with self._lock: return self._moods.get(patient)

    def audit(self, actor, rid):
        with self._lock:
            self._get(actor, rid, clinical=True)
            return deepcopy([e for e in self._audit if e['record_id']==rid])
