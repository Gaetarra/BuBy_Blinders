from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, false, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import richiedi_ruoli, utente_corrente
from ..email_uscita import accoda_stato_segnalazione
from ..models import NotaInterna, Prenotazione, Segnalazione, Utente, Veicolo
from ..schemas import (
    NotaIn,
    NotaOut,
    SegnalazioneAggiorna,
    SegnalazioneIn,
    SegnalazioneOut,
)

router = APIRouter(prefix="/segnalazioni", tags=["segnalazioni"])


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _solo_visibili(query, utente: Utente):
    """Il cliente vede le proprie; l'operatore quelle della sua sede (o non ancora smistate); l'admin tutte."""
    if utente.ruolo == "cliente":
        if utente.cliente_id is None:
            return query.where(false())
        return query.where(Segnalazione.cliente_id == utente.cliente_id)
    if utente.ruolo == "operatore":
        veicoli_sede = select(Veicolo.id).where(Veicolo.sede_id == utente.sede_id)
        return query.where(
            or_(
                and_(Segnalazione.veicolo_id.is_(None), Segnalazione.sede_id.is_(None)),
                Segnalazione.sede_id == utente.sede_id,
                Segnalazione.veicolo_id.in_(veicoli_sede),
            )
        )
    return query


def _trova_visibile(db: Session, segnalazione_id: int, utente: Utente) -> Segnalazione:
    query = _solo_visibili(select(Segnalazione).where(Segnalazione.id == segnalazione_id), utente)
    segnalazione = db.scalar(query)
    if segnalazione is None:
        raise HTTPException(404, "Segnalazione non trovata")
    return segnalazione


@router.post("", response_model=SegnalazioneOut, status_code=201)
def crea(
    dati: SegnalazioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    cliente_id = utente.cliente_id if utente.ruolo == "cliente" else dati.cliente_id
    veicolo_id = dati.veicolo_id
    if dati.prenotazione_id is not None:
        prenotazione = db.get(Prenotazione, dati.prenotazione_id)
        if prenotazione is None or (
            utente.ruolo == "cliente" and prenotazione.cliente_id != cliente_id
        ):
            raise HTTPException(404, "Prenotazione non trovata")
        veicolo_id = veicolo_id or prenotazione.veicolo_id
    veicolo = db.get(Veicolo, veicolo_id) if veicolo_id is not None else None
    if veicolo_id is not None and veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")

    segnalazione = Segnalazione(
        veicolo_id=veicolo_id,
        prenotazione_id=dati.prenotazione_id,
        cliente_id=cliente_id,
        mittente_email=utente.email,
        oggetto=dati.oggetto,
        testo=dati.testo,
        ricevuta_il=_adesso(),
        stato="nuova",
        canale="app",
        sede_id=veicolo.sede_id if veicolo else None,
    )
    db.add(segnalazione)
    db.commit()
    db.refresh(segnalazione)
    return segnalazione


@router.get("", response_model=list[SegnalazioneOut])
def elenco(
    stato: str | None = None,
    categoria: str | None = None,
    urgenza: str | None = None,
    veicolo_id: int | None = None,
    sede_id: int | None = None,
    canale: str | None = None,
    assegnata_a: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    query = _solo_visibili(select(Segnalazione), utente)
    for colonna, valore in (
        (Segnalazione.stato, stato),
        (Segnalazione.categoria, categoria),
        (Segnalazione.urgenza, urgenza),
        (Segnalazione.veicolo_id, veicolo_id),
        (Segnalazione.sede_id, sede_id),
        (Segnalazione.canale, canale),
        (Segnalazione.assegnata_a, assegnata_a),
    ):
        if valore is not None:
            query = query.where(colonna == valore)
    query = query.order_by(Segnalazione.ricevuta_il.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/{segnalazione_id}", response_model=SegnalazioneOut)
def dettaglio(
    segnalazione_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    return _trova_visibile(db, segnalazione_id, utente)


@router.patch("/{segnalazione_id}", response_model=SegnalazioneOut)
def aggiorna(
    segnalazione_id: int,
    dati: SegnalazioneAggiorna,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    segnalazione = _trova_visibile(db, segnalazione_id, utente)
    campi = dati.model_dump(exclude_unset=True)
    if campi.get("assegnata_a") is not None:
        assegnatario = db.get(Utente, campi["assegnata_a"])
        if assegnatario is None or assegnatario.ruolo not in ("operatore", "admin"):
            raise HTTPException(422, "assegnata_a deve essere un operatore o un admin")
    stato_precedente = segnalazione.stato
    for campo, valore in campi.items():
        setattr(segnalazione, campo, valore)
    if segnalazione.stato != stato_precedente:
        accoda_stato_segnalazione(db, segnalazione)  # avviso al cliente, nella stessa transazione
    db.commit()
    db.refresh(segnalazione)
    return segnalazione


@router.post("/{segnalazione_id}/note", response_model=NotaOut, status_code=201)
def aggiungi_nota(
    segnalazione_id: int,
    dati: NotaIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    """Nota interna: non e mai visibile al cliente."""
    segnalazione = _trova_visibile(db, segnalazione_id, utente)
    nota = NotaInterna(
        segnalazione_id=segnalazione.id, autore_id=utente.id, testo=dati.testo, creata_il=_adesso()
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


@router.get("/{segnalazione_id}/note", response_model=list[NotaOut])
def elenco_note(
    segnalazione_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    segnalazione = _trova_visibile(db, segnalazione_id, utente)
    return list(
        db.scalars(
            select(NotaInterna)
            .where(NotaInterna.segnalazione_id == segnalazione.id)
            .order_by(NotaInterna.creata_il)
        )
    )
