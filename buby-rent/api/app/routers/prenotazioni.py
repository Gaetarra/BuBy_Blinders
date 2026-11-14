from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..availability import ha_sovrapposizioni
from ..database import get_db
from ..deps import utente_corrente
from ..email_uscita import accoda_email
from ..models import STATI_NON_NOLEGGIABILI, Cliente, Prenotazione, Utente, Veicolo
from ..schemas import PrenotazioneIn, PrenotazioneOut

router = APIRouter(prefix="/prenotazioni", tags=["prenotazioni"])


def _data_leggibile(data) -> str:
    return data.strftime("%d/%m/%Y alle %H:%M")


@router.post("", response_model=PrenotazioneOut, status_code=201)
def crea(
    dati: PrenotazioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    if utente.ruolo == "ceo":
        raise HTTPException(403, "Il CEO ha accesso in sola lettura")
    if utente.ruolo == "cliente":
        cliente_id = utente.cliente_id  # un cliente prenota solo per se stesso
    elif dati.cliente_id is not None:
        cliente_id = dati.cliente_id
    else:
        raise HTTPException(422, "cliente_id obbligatorio per operatori e admin")

    # blocca la riga del veicolo: due richieste simultanee sullo stesso mezzo si accodano
    veicolo = db.scalar(
        select(Veicolo).where(Veicolo.id == dati.veicolo_id).with_for_update()
    )
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    if db.get(Cliente, cliente_id) is None:
        raise HTTPException(404, "Cliente non trovato")
    if veicolo.stato in STATI_NON_NOLEGGIABILI:
        raise HTTPException(409, "Veicolo non noleggiabile")
    if db.scalar(select(ha_sovrapposizioni(veicolo.id, dati.inizio, dati.fine))):
        raise HTTPException(409, "Veicolo gia prenotato nel periodo richiesto")

    prenotazione = Prenotazione(
        veicolo_id=veicolo.id,
        cliente_id=cliente_id,
        inizio=dati.inizio,
        fine=dati.fine,
        stato="confermata",
    )
    db.add(prenotazione)
    db.flush()
    cliente = db.get(Cliente, cliente_id)
    if not cliente.email.endswith("@anonimo.invalid"):
        accoda_email(
            db,
            destinatario=cliente.email,
            oggetto=f"Prenotazione BR-{prenotazione.id:06d} confermata",
            corpo=(
                f"La prenotazione per il veicolo {veicolo.targa} è stata confermata. "
                f"Periodo: {_data_leggibile(dati.inizio)} - {_data_leggibile(dati.fine)}."
            ),
        )
    db.commit()
    db.refresh(prenotazione)
    return prenotazione


@router.get("", response_model=list[PrenotazioneOut])
def elenco(
    cliente_id: int | None = None,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    query = select(Prenotazione).order_by(Prenotazione.inizio.desc())
    if utente.ruolo == "cliente":
        query = query.where(Prenotazione.cliente_id == utente.cliente_id)  # solo le proprie
    elif cliente_id is not None:
        query = query.where(Prenotazione.cliente_id == cliente_id)
    return list(db.scalars(query))
