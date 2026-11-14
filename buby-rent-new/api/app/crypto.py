import hashlib
import hmac

from cryptography.fernet import Fernet, MultiFernet

from .config import settings


def _fernet() -> MultiFernet:
    # la prima chiave cifra; le altre servono solo a decifrare (rotazione delle chiavi)
    return MultiFernet([Fernet(k.encode()) for k in settings.encryption_keys])


def cifra(testo: str) -> str:
    return _fernet().encrypt(testo.encode("utf-8")).decode()


def decifra(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode("utf-8")


def blind_index(valore: str) -> str:
    """Impronta HMAC con chiave separata: permette di cercare e rendere unico un
    valore cifrato (es. l'email) senza salvarlo in chiaro."""
    normalizzato = valore.strip().lower()
    return hmac.new(
        settings.blind_index_key.encode(), normalizzato.encode("utf-8"), hashlib.sha256
    ).hexdigest()
