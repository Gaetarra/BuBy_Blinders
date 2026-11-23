from datetime import datetime

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from .models import (
    STATI_ATTIVI,
    STATI_NON_NOLEGGIABILI,
    Manutenzione,
    Prenotazione,
    Trasferimento,
    Veicolo,
)

STATI_MANUTENZIONE_ATTIVI = ("programmata", "in_corso")
STATI_TRASFERIMENTO_ATTIVI = ("programmato", "in_corso")


def _periodo_sovrapposto(col_inizio, col_fine, inizio: datetime, fine: datetime):
    """True se [col_inizio, col_fine] (anche con estremi NULL) si sovrappone a [inizio, fine]."""
    return and_(
        or_(col_inizio.is_(None), col_inizio < fine),
        or_(col_fine.is_(None), col_fine > inizio),
    )


def ha_sovrapposizioni(veicolo_id, inizio: datetime, fine: datetime):
    """True se il veicolo ha prenotazioni, manutenzioni o trasferimenti attivi nel periodo."""
    sovrapposizione_prenotazione = exists().where(
        Prenotazione.veicolo_id == veicolo_id,
        Prenotazione.stato.in_(STATI_ATTIVI),
        Prenotazione.inizio < fine,
        Prenotazione.fine > inizio,
    )
    sovrapposizione_manutenzione = exists().where(
        Manutenzione.veicolo_id == veicolo_id,
        Manutenzione.stato.in_(STATI_MANUTENZIONE_ATTIVI),
        _periodo_sovrapposto(Manutenzione.inizio, Manutenzione.fine, inizio, fine),
    )
    sovrapposizione_trasferimento = exists().where(
        Trasferimento.veicolo_id == veicolo_id,
        Trasferimento.stato.in_(STATI_TRASFERIMENTO_ATTIVI),
        _periodo_sovrapposto(Trasferimento.inizio, Trasferimento.fine, inizio, fine),
    )
    return or_(
        sovrapposizione_prenotazione,
        sovrapposizione_manutenzione,
        sovrapposizione_trasferimento,
    )


def veicoli_disponibili(
    db: Session, sede_id: int, inizio: datetime, fine: datetime, tipo: str | None = None
) -> list[Veicolo]:
    query = select(Veicolo).where(
        Veicolo.sede_id == sede_id,
        Veicolo.stato.not_in(STATI_NON_NOLEGGIABILI),
        ~ha_sovrapposizioni(Veicolo.id, inizio, fine),
    )
    if tipo:
        query = query.where(Veicolo.tipo == tipo)
    return list(db.scalars(query.order_by(Veicolo.id)))