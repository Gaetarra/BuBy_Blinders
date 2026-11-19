from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import IdentitaSupabase, Utente
from .security import leggi_token
from .supabase_auth import (
    SupabaseConfigurationError,
    SupabaseJwksUnavailable,
    SupabaseTokenRejected,
    verifica_token_supabase,
)

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class IdentitaAutenticataSupabase:
    token: str
    supabase_id: str


def identita_supabase(token: str = Depends(oauth2)) -> IdentitaAutenticataSupabase:
    non_autenticato = HTTPException(
        401, "Token Supabase non valido", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = verifica_token_supabase(token)
    except SupabaseConfigurationError as error:
        raise HTTPException(503, str(error)) from error
    except SupabaseJwksUnavailable as error:
        raise HTTPException(503, "Verifica delle chiavi Supabase non disponibile") from error
    except SupabaseTokenRejected as error:
        raise non_autenticato from error
    return IdentitaAutenticataSupabase(token=token, supabase_id=payload["sub"])


def utente_corrente(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Utente:
    non_autenticato = HTTPException(
        401, "Credenziali non valide", headers={"WWW-Authenticate": "Bearer"}
    )
    if settings.supabase_url:
        try:
            payload = verifica_token_supabase(token)
        except SupabaseConfigurationError as error:
            raise HTTPException(503, str(error)) from error
        except SupabaseJwksUnavailable as error:
            raise HTTPException(
                503, "Verifica delle chiavi Supabase non disponibile"
            ) from error
        except SupabaseTokenRejected as error:
            raise non_autenticato from error

        identita = db.get(IdentitaSupabase, payload["sub"])
        utente = db.get(Utente, identita.utente_id) if identita else None
        if utente is None:
            raise HTTPException(
                403,
                "Account Supabase non collegato: completa POST /auth/supabase/provision",
            )
        return utente

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
