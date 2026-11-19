import json
import uuid
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError

from .config import settings

SUPABASE_JWT_ALGORITHMS = ("ES256", "RS256")


class SupabaseConfigurationError(Exception):
    pass


class SupabaseJwksUnavailable(Exception):
    pass


class SupabaseServiceUnavailable(Exception):
    pass


class SupabaseTokenRejected(Exception):
    pass


@lru_cache(maxsize=2)
def _jwk_client(project_url: str) -> PyJWKClient:
    return PyJWKClient(
        f"{project_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        timeout=5,
    )


def verifica_token_supabase(token: str) -> dict:
    project_url = settings.supabase_url
    if not project_url:
        raise SupabaseConfigurationError("SUPABASE_URL non configurato")
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in SUPABASE_JWT_ALGORITHMS:
            raise SupabaseTokenRejected("Algoritmo JWT Supabase non supportato")
        signing_key = _jwk_client(project_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(SUPABASE_JWT_ALGORITHMS),
            audience="authenticated",
            issuer=f"{project_url.rstrip('/')}/auth/v1",
            options={"require": ["exp", "sub", "aud", "iss", "role"]},
        )
        if payload.get("role") != "authenticated":
            raise SupabaseTokenRejected("Il token non è un access token utente")
        payload["sub"] = str(uuid.UUID(payload["sub"]))
        return payload
    except PyJWKClientConnectionError as error:
        raise SupabaseJwksUnavailable from error
    except (jwt.PyJWTError, PyJWKClientError, ValueError, TypeError) as error:
        raise SupabaseTokenRejected from error


def recupera_utente_supabase(token: str) -> dict:
    project_url = settings.supabase_url
    publishable_key = settings.supabase_publishable_key
    if not project_url or not publishable_key:
        raise SupabaseConfigurationError(
            "SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY sono necessari per collegare account"
        )

    request = Request(
        f"{project_url.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": publishable_key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=5) as response:
            utente = json.load(response)
    except HTTPError as error:
        if error.code in (401, 403):
            raise SupabaseTokenRejected from error
        raise SupabaseServiceUnavailable from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise SupabaseServiceUnavailable from error

    if not isinstance(utente, dict):
        raise SupabaseServiceUnavailable("Risposta utente Supabase non valida")
    return utente
