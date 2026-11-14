from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crypto import blind_index
from ..database import get_db
from ..deps import utente_corrente
from ..models import (
    STATI_ATTIVI,
    Cliente,
    EmailDaInviare,
    NotaInterna,
    Prenotazione,
    Segnalazione,
    Utente,
)
from ..schemas import (
    AggiornaProfiloIn,
    ClienteDati,
    EsportazioneDati,
    PrenotazioneOut,
    RegistrazioneIn,
    SegnalazioneOut,
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
    if db.scalar(select(Utente.id).where(Utente.email_idx == indice)):
        raise HTTPException(409, "Email gia registrata")
    cliente = db.scalar(select(Cliente).where(Cliente.email_idx == indice))
    if cliente is not None:
        # anagrafica gia presente (cliente importato dal dataset, senza account)
        if not settings.collega_clienti_importati or db.scalar(
            select(Utente.id).where(Utente.cliente_id == cliente.id)
        ):
            raise HTTPException(409, "Email gia registrata")
    else:
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
    segnalazioni = []
    if cliente is not None:
        segnalazioni = list(
            db.scalars(
                select(Segnalazione)
                .where(Segnalazione.cliente_id == cliente.id)
                .order_by(Segnalazione.ricevuta_il)
            )
        )
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
        segnalazioni=[SegnalazioneOut.model_validate(x) for x in segnalazioni],
    )


@router.delete("/me", status_code=204)
def cancella_account(db: Session = Depends(get_db), utente: Utente = Depends(utente_corrente)):
    """Diritto alla cancellazione (art. 17 GDPR).

    L'account viene eliminato e l'anagrafica anonimizzata; il testo delle segnalazioni viene
    rimosso (restano categoria e urgenza); note interne ed email in coda o nel log vengono svuotate. Le prenotazioni restano, senza dati identificativi, perche contratti e fatture vanno conservati per obbligo di legge
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
    # i testi liberi possono contenere dati personali e non c'e obbligo di conservarli
    for segnalazione in db.scalars(
        select(Segnalazione).where(Segnalazione.cliente_id == utente.cliente_id)
    ):
        for nota in db.scalars(
            select(NotaInterna).where(NotaInterna.segnalazione_id == segnalazione.id)
        ):
            nota.testo = "[rimosso]"
        segnalazione.mittente_email = None
        segnalazione.oggetto = None
        segnalazione.sintesi = None
        segnalazione.testo = "[contenuto rimosso su richiesta dell'interessato]"
    cliente = db.get(Cliente, utente.cliente_id)
    # email in coda o gia inviate a questo indirizzo: annulla quelle non partite e svuota il log
    for email in db.scalars(
        select(EmailDaInviare).where(EmailDaInviare.destinatario_idx == blind_index(cliente.email))
    ):
        if email.stato == "da_inviare":
            email.stato = "annullata"
        email.destinatario = "eliminato@anonimo.invalid"
        email.oggetto = "[rimosso]"
        email.corpo = "[rimosso]"
    cliente.nome = "Utente eliminato"
    cliente.email = f"eliminato-{cliente.id}@anonimo.invalid"
    cliente.anonimizzato_il = _adesso()
    db.delete(utente)
    db.commit()
    return Response(status_code=204)
