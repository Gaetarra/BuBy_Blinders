from datetime import datetime, timezone
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crypto import blind_index
from ..database import get_db
from ..deps import IdentitaAutenticataSupabase, identita_supabase, utente_corrente
from ..models import STATI_ATTIVI, Cliente, IdentitaSupabase, Prenotazione, Utente
from ..schemas import (
    AggiornaProfiloIn,
    ClienteDati,
    CollegamentoSupabaseIn,
    EsportazioneDati,
    PrenotazioneOut,
    RegistrazioneIn,
    Token,
    UtenteOut,
)
from ..security import HASH_FINTO, crea_token, hash_password, verify_password
from ..supabase_auth import (
    SupabaseConfigurationError,
    SupabaseServiceUnavailable,
    SupabaseTokenRejected,
    recupera_utente_supabase,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _richiedi_auth_locale_disattivata():
    if settings.supabase_url:
        raise HTTPException(
            410,
            "Autenticazione locale disattivata: usa Supabase Auth e POST /auth/supabase/provision",
        )


@router.post("/register", response_model=UtenteOut, status_code=201)
def registrazione(dati: RegistrazioneIn, db: Session = Depends(get_db)):
    _richiedi_auth_locale_disattivata()
    indice = blind_index(dati.email)
    esiste = db.scalar(select(Utente.id).where(Utente.email_idx == indice)) or db.scalar(
        select(Cliente.id).where(Cliente.email_idx == indice)
    )
    if esiste:
        raise HTTPException(409, "Email gia registrata")
    cliente = Cliente(tipo=dati.tipo, nome=dati.nome.strip(), email=dati.email)
    db.add(cliente)
    db.flush()
    utente = Utente(
        email=dati.email,
        password_hash=hash_password(dati.password),
        ruolo="cliente",  # operatori e admin non si auto-registrano
        cliente_id=cliente.id,
        privacy_versione=settings.privacy_versione,
        privacy_accettata_il=_adesso(),
    )
    db.add(utente)
    db.commit()
    db.refresh(utente)
    return utente


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    _richiedi_auth_locale_disattivata()
    utente = db.scalar(select(Utente).where(Utente.email_idx == blind_index(form.username)))
    hash_da_controllare = utente.password_hash if utente else HASH_FINTO
    password_ok = verify_password(form.password, hash_da_controllare)
    if utente is None or not password_ok:
        raise HTTPException(
            401, "Email o password errate", headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(access_token=crea_token(utente.id, utente.ruolo))


@router.post("/supabase/provision", response_model=UtenteOut)
def collega_account_supabase(
    dati: CollegamentoSupabaseIn,
    db: Session = Depends(get_db),
    identita: IdentitaAutenticataSupabase = Depends(identita_supabase),
):
    try:
        account_supabase = recupera_utente_supabase(identita.token)
    except SupabaseConfigurationError as error:
        raise HTTPException(503, str(error)) from error
    except SupabaseTokenRejected as error:
        raise HTTPException(
            401, "Sessione Supabase non valida", headers={"WWW-Authenticate": "Bearer"}
        ) from error
    except SupabaseServiceUnavailable as error:
        raise HTTPException(503, "Servizio Supabase non disponibile") from error

    try:
        account_id = str(uuid.UUID(account_supabase.get("id", "")))
    except (ValueError, TypeError, AttributeError) as error:
        raise HTTPException(401, "Identità Supabase non valida") from error
    if account_id != identita.supabase_id:
        raise HTTPException(401, "Identità Supabase non corrispondente")

    email = account_supabase.get("email")
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(422, "L'account Supabase deve avere un'email")
    if not account_supabase.get("email_confirmed_at"):
        raise HTTPException(403, "Verifica l'email Supabase prima di collegare l'account")

    collegamento = db.get(IdentitaSupabase, identita.supabase_id)
    if collegamento:
        utente = db.get(Utente, collegamento.utente_id)
        if utente is None:
            raise HTTPException(409, "Collegamento Supabase non coerente")
        return utente

    indice_email = blind_index(email)
    utente = db.scalar(select(Utente).where(Utente.email_idx == indice_email))
    cliente = db.scalar(select(Cliente).where(Cliente.email_idx == indice_email))

    if utente is None:
        if not dati.accetta_privacy:
            raise HTTPException(422, "Per creare il profilo cliente devi accettare l'informativa")
        if cliente is None:
            if not dati.nome or not dati.nome.strip():
                raise HTTPException(422, "Il nome è obbligatorio per creare il profilo cliente")
            cliente = Cliente(
                tipo=dati.tipo,
                nome=dati.nome.strip(),
                email=email,
            )
            db.add(cliente)
            db.flush()
        utente = Utente(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            ruolo="cliente",
            cliente_id=cliente.id,
            privacy_versione=settings.privacy_versione,
            privacy_accettata_il=_adesso(),
        )
        db.add(utente)
        db.flush()
    elif utente.ruolo == "cliente":
        if utente.cliente_id is None:
            if cliente is None:
                if not dati.accetta_privacy:
                    raise HTTPException(
                        422, "Per creare il profilo cliente devi accettare l'informativa"
                    )
                if not dati.nome or not dati.nome.strip():
                    raise HTTPException(
                        422, "Il nome è obbligatorio per creare il profilo cliente"
                    )
                cliente = Cliente(
                    tipo=dati.tipo,
                    nome=dati.nome.strip(),
                    email=email,
                )
                db.add(cliente)
                db.flush()
            utente.cliente_id = cliente.id
        if utente.privacy_versione is None:
            if not dati.accetta_privacy:
                raise HTTPException(
                    422, "Per collegare il profilo cliente devi accettare l'informativa"
                )
            utente.privacy_versione = settings.privacy_versione
            utente.privacy_accettata_il = _adesso()

    altro_collegamento = db.scalar(
        select(IdentitaSupabase).where(IdentitaSupabase.utente_id == utente.id)
    )
    if altro_collegamento:
        raise HTTPException(409, "L'account applicativo è già collegato a un'altra identità")

    db.add(
        IdentitaSupabase(
            supabase_id=identita.supabase_id,
            utente_id=utente.id,
        )
    )
    db.commit()
    db.refresh(utente)
    return utente


@router.get("/me", response_model=UtenteOut)
def profilo(utente: Utente = Depends(utente_corrente)):
    return utente


@router.patch("/me", response_model=ClienteDati)
def rettifica(
    dati: AggiornaProfiloIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    """Diritto di rettifica (art. 16 GDPR): il cliente corregge il proprio nome."""
    cliente = db.get(Cliente, utente.cliente_id) if utente.cliente_id else None
    if cliente is None:
        raise HTTPException(403, "Solo i clienti hanno un profilo anagrafico")
    cliente.nome = dati.nome.strip()
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("/me/dati", response_model=EsportazioneDati)
def esporta_dati(db: Session = Depends(get_db), utente: Utente = Depends(utente_corrente)):
    """Diritto di accesso e portabilita (artt. 15 e 20 GDPR): tutti i dati dell'utente in JSON."""
    cliente = db.get(Cliente, utente.cliente_id) if utente.cliente_id else None
    prenotazioni = []
    if cliente is not None:
        prenotazioni = list(
            db.scalars(
                select(Prenotazione)
                .where(Prenotazione.cliente_id == cliente.id)
                .order_by(Prenotazione.inizio)
            )
        )
    return EsportazioneDati(
        utente=UtenteOut.model_validate(utente),
        privacy_versione=utente.privacy_versione,
        privacy_accettata_il=utente.privacy_accettata_il,
        cliente=ClienteDati.model_validate(cliente) if cliente else None,
        prenotazioni=[PrenotazioneOut.model_validate(p) for p in prenotazioni],
    )


@router.delete("/me", status_code=204)
def cancella_account(db: Session = Depends(get_db), utente: Utente = Depends(utente_corrente)):
    """Diritto alla cancellazione (art. 17 GDPR).

    L'account viene eliminato e l'anagrafica anonimizzata. Le prenotazioni restano, senza
    dati identificativi, perche contratti e fatture vanno conservati per obbligo di legge
    (art. 17, par. 3, lett. b)."""
    if utente.ruolo != "cliente" or utente.cliente_id is None:
        raise HTTPException(403, "Solo i clienti possono cancellare il proprio account da qui")
    attive = db.scalar(
        select(Prenotazione.id)
        .where(
            Prenotazione.cliente_id == utente.cliente_id,
            Prenotazione.stato.in_(STATI_ATTIVI),
            Prenotazione.fine > _adesso(),
        )
        .limit(1)
    )
    if attive:
        raise HTTPException(409, "Hai prenotazioni attive: annullale o attendi la riconsegna")
    cliente = db.get(Cliente, utente.cliente_id)
    cliente.nome = "Utente eliminato"
    cliente.email = f"eliminato-{cliente.id}@anonimo.invalid"
    cliente.anonimizzato_il = _adesso()
    collegamento = db.scalar(
        select(IdentitaSupabase).where(IdentitaSupabase.utente_id == utente.id)
    )
    if collegamento:
        db.delete(collegamento)
    db.delete(utente)
    db.commit()
    return Response(status_code=204)
