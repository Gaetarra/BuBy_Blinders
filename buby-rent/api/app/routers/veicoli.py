from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..availability import veicoli_disponibili
from ..database import get_db
from ..deps import richiedi_ruoli
from ..models import Utente, Veicolo
from ..schemas import StatoIn, VeicoloOut

router = APIRouter(prefix="/veicoli", tags=["veicoli"])


@router.get("/disponibili", response_model=list[VeicoloOut])
def disponibili(
    sede_id: int,
    da: datetime,
    a: datetime = Query(..., description="Fine del periodo"),
    tipo: str | None = None,
    db: Session = Depends(get_db),
):
    """Ricerca pubblica: non richiede login."""
    return veicoli_disponibili(db, sede_id, da, a, tipo)


@router.patch("/{veicolo_id}/stato", response_model=VeicoloOut)
def cambia_stato(
    veicolo_id: int,
    dati: StatoIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    if utente.ruolo == "operatore" and utente.sede_id != veicolo.sede_id:
        raise HTTPException(403, "Puoi gestire solo i veicoli della tua sede")
    veicolo.stato = dati.stato
    db.commit()
    db.refresh(veicolo)
    return veicolo
