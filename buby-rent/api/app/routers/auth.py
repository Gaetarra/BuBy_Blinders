from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crypto import blind_index
from ..database import get_db
from ..deps import utente_corrente
from ..models import STATI_ATTIVI, Cliente, Prenotazione, Utente
from ..schemas import (
    AggiornaProfiloIn,
    ClienteDati,
    EsportazioneDati,
    PrenotazioneOut,
    RegistrazioneIn,
    Token,
    UtenteOut,
)
from ..security import HASH_FINTO, crea_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/register", response_model=UtenteOut, status_code=201)
def registrazione(dati: RegistrazioneIn, db: Session = Depends(get_db)):
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
    utente = db.scalar(select(Utente).where(Utente.email_idx == blind_index(form.username)))
    hash_da_controllare = utente.password_hash if utente else HASH_FINTO
    password_ok = verify_password(form.password, hash_da_controllare)
    if utente is None or not password_ok:
        raise HTTPException(
            401, "Email o password errate", headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(access_token=crea_token(utente.id, utente.ruolo))


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
    db.delete(utente)
    db.commit()
    return Response(status_code=204)
