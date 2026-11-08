from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings


def _bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]  # limite di bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bytes(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bytes(password), password_hash.encode())
    except ValueError:
        return False


def crea_token(utente_id: int, ruolo: str) -> str:
    adesso = datetime.now(timezone.utc)
    payload = {
        "sub": str(utente_id),
        "ruolo": ruolo,
        "iat": adesso,
        "exp": adesso + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def leggi_token(token: str) -> dict:
    """Solleva jwt.PyJWTError se il token e scaduto, alterato o malformato."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )


HASH_FINTO = hash_password("password-finta")  # per tempi di risposta simili nel login
