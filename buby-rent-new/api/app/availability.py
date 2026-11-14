from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from .models import STATI_ATTIVI, STATI_NON_NOLEGGIABILI, Prenotazione, Veicolo


def ha_sovrapposizioni(veicolo_id, inizio: datetime, fine: datetime):
    """Due periodi si sovrappongono se inizio_A < fine_B e fine_A > inizio_B."""
    return exists().where(
        Prenotazione.veicolo_id == veicolo_id,
        Prenotazione.stato.in_(STATI_ATTIVI),
        Prenotazione.inizio < fine,
        Prenotazione.fine > inizio,
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
