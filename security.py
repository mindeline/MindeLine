"""Server-side identity and authorization; no credentials in application code."""
from dataclasses import dataclass

ROLES = frozenset({'Paciente', 'Enfermería', 'Equipo tratante'})

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    patients: frozenset[str]
    demo: bool = False

    def authorize(self, patient, *, clinical=False):
        if self.role not in ROLES or patient not in self.patients:
            raise PermissionError('Access denied')
        if clinical and self.role not in {'Enfermería', 'Equipo tratante'}:
            raise PermissionError('Clinical role required')


def resolve_principal(claims, access):
    """Match the immutable OIDC issuer + subject, never a user-editable email."""
    issuer, subject = claims.get('iss'), claims.get('sub')
    if not isinstance(issuer, str) or not issuer or not isinstance(subject, str) or not subject:
        raise PermissionError('Missing identity')
    matches = [u for u in access if u.get('issuer') == issuer and u.get('subject') == subject]
    if len(matches) != 1:
        raise PermissionError('Account not authorized')
    row = matches[0]
    patients = row.get('patients')
    if row.get('role') not in ROLES or not isinstance(patients, (list, tuple)) or not patients:
        raise PermissionError('Invalid access configuration')
    if any(not isinstance(p, str) or not p.strip() for p in patients):
        raise PermissionError('Invalid patient assignment')
    if row['role'] == 'Paciente' and len(patients) != 1:
        raise PermissionError('Patient account must have exactly one assignment')
    return Principal(issuer + '|' + subject, row['role'], frozenset(patients))
