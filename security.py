"""Server-side identity and authorization; no credentials in application code."""
from dataclasses import dataclass
import base64
import hashlib
import hmac
import re
import secrets

ROLES = frozenset({'Paciente', 'Enfermería', 'Equipo tratante'})
_PASSWORD_SCHEME = 'pbkdf2_sha256'
_PASSWORD_ITERATIONS = 310_000
_USERNAME = re.compile(r'^[a-zA-Z0-9._-]{3,64}$')

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


def hash_demo_password(password):
    """Return a salted password hash for a locally configured prototype account."""
    if not isinstance(password, str) or len(password) < 12 or len(password) > 1024:
        raise ValueError('Password must be between 12 and 1024 characters')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, _PASSWORD_ITERATIONS
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')
    return f'{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${encode(salt)}${encode(digest)}'


def _valid_demo_users(users):
    if not isinstance(users, (list, tuple)) or not users:
        raise PermissionError('Demo accounts are not configured')
    accounts = {}
    for row in users:
        if not isinstance(row, dict):
            raise PermissionError('Invalid demo account configuration')
        username = row.get('username')
        role = row.get('role')
        patients = row.get('patients')
        password_hash = row.get('password_hash')
        if (not isinstance(username, str) or not _USERNAME.fullmatch(username)
                or role not in ROLES
                or not isinstance(patients, (list, tuple)) or not patients
                or any(not isinstance(p, str) or not p.strip() for p in patients)
                or not isinstance(password_hash, str)):
            raise PermissionError('Invalid demo account configuration')
        key = username.casefold()
        if key in accounts:
            raise PermissionError('Duplicate demo username')
        if role == 'Paciente' and len(patients) != 1:
            raise PermissionError('Patient account must have exactly one assignment')
        accounts[key] = row
    return accounts


def _verify_demo_password(password, encoded):
    if not isinstance(password, str) or len(password) > 1024:
        return False
    try:
        scheme, iterations_text, salt_text, digest_text = encoded.split('$')
        iterations = int(iterations_text)
        if scheme != _PASSWORD_SCHEME or not 100_000 <= iterations <= 1_000_000:
            return False
        decode = lambda value: base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
        salt, expected = decode(salt_text), decode(digest_text)
        if len(salt) < 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def resolve_demo_principal(username, password, users):
    """Authenticate one explicitly configured local demo account."""
    accounts = _valid_demo_users(users)
    if not isinstance(username, str) or not isinstance(password, str):
        raise PermissionError('Invalid credentials')
    row = accounts.get(username.strip().casefold())
    if row is None or not _verify_demo_password(password, row['password_hash']):
        raise PermissionError('Invalid credentials')
    return Principal(
        'demo:' + row['username'].casefold(),
        row['role'],
        frozenset(row['patients']),
        demo=True,
    )


def validate_demo_users(users):
    """Validate demo account configuration before displaying a login form."""
    _valid_demo_users(users)
