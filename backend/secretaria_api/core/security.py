"""Seguridad: hash de contraseñas y tokens firmados.

Se usa PBKDF2-HMAC-SHA256 (stdlib) y itsdangerous para los tokens, de modo que
el proyecto no dependa de binarios externos como bcrypt/cryptography.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings

PBKDF2_ITERATIONS = 260_000
_PASSWORD_PREFIX = "pbkdf2_sha256"

serializer = URLSafeTimedSerializer(settings.secret_key, salt="secretaria-virtual-auth")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"{_PASSWORD_PREFIX}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        prefix, iterations, salt, digest = stored.split("$")
        if prefix != _PASSWORD_PREFIX:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        )
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, rol: str) -> str:
    payload = {
        "sub": subject,
        "rol": rol,
        "iat": datetime.now(timezone.utc).isoformat(),
    }
    return serializer.dumps(payload)


def decode_access_token(token: str) -> dict | None:
    try:
        return serializer.loads(token, max_age=settings.access_token_expire_minutes * 60)
    except (BadSignature, SignatureExpired):
        return None
