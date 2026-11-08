import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Utente
from .security import leggi_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def utente_corrente(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Utente:
    non_autenticato = HTTPException(
        401, "Credenziali non valide", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = leggi_token(token)
        utente_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise non_autenticato
    utente = db.get(Utente, utente_id)
    if utente is None:
        raise non_autenticato
    return utente  # il ruolo si legge dal database, non dal token


def richiedi_ruoli(*ruoli: str):
    def controlla(utente: Utente = Depends(utente_corrente)) -> Utente:
        if utente.ruolo not in ruoli:
            raise HTTPException(403, "Permessi insufficienti")
        return utente

    return controlla
