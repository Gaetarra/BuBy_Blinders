"""Punto unico di ingresso dei messaggi: ogni canale (email, CSV, app) chiama ricevi_messaggio."""
import re
import unicodedata
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .crypto import blind_index
from .models import Cliente, Prenotazione, Sede, Segnalazione, Veicolo

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODICE_PRENOTAZIONE = re.compile(r"\bBR-(\d{1,9})\b", re.IGNORECASE)


def _slug(testo: str) -> str:
    senza_accenti = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", senza_accenti.lower())


def sede_da_indirizzo(db: Session, destinatario: str | None) -> Sede | None:
    """assistenza.torino@dominio -> sede la cui citta e Torino."""
    if not destinatario or "@" not in destinatario:
        return None
    parte_locale = destinatario.split("@")[0]
    if "." not in parte_locale:
        return None
    slug = _slug(parte_locale.split(".", 1)[1])
    for sede in db.scalars(select(Sede)):
        if _slug(sede.citta) == slug:
            return sede
    return None


def ricevi_messaggio(
    db: Session,
    *,
    mittente: str,
    destinatario: str | None,
    oggetto: str | None,
    testo: str | None,
    data: datetime,
    message_id: str | None = None,
    in_reply_to: str | None = None,
    canale: str = "email",
) -> Segnalazione | None:
    """Crea una segnalazione da un messaggio. Non fa commit. Restituisce None se il messaggio
    e da scartare (indirizzo non valido, testo vuoto, duplicato)."""
    mittente = (mittente or "").strip().lower()
    testo = (testo or "").strip()
    if not EMAIL.match(mittente) or not testo:
        return None
    if message_id and db.scalar(select(Segnalazione.id).where(Segnalazione.message_id == message_id)):
        return None

    cliente = db.scalar(select(Cliente).where(Cliente.email_idx == blind_index(mittente)))
    veicolo_id = prenotazione_id = sede_id = None

    # il mittente di una email non e autenticato: si collega una prenotazione solo se e sua
    trovato = CODICE_PRENOTAZIONE.search(oggetto or "")
    if trovato and cliente is not None:
        prenotazione = db.get(Prenotazione, int(trovato.group(1)))
        if prenotazione is not None and prenotazione.cliente_id == cliente.id:
            prenotazione_id, veicolo_id = prenotazione.id, prenotazione.veicolo_id

    if in_reply_to:
        padre = db.scalar(select(Segnalazione).where(Segnalazione.message_id == in_reply_to))
        if padre is not None and (padre.mittente_email or "").lower() == mittente:
            prenotazione_id = prenotazione_id or padre.prenotazione_id
            veicolo_id = veicolo_id or padre.veicolo_id
            sede_id = padre.sede_id

    if veicolo_id is not None and sede_id is None:
        veicolo = db.get(Veicolo, veicolo_id)
        sede_id = veicolo.sede_id if veicolo else None
    if sede_id is None:
        sede = sede_da_indirizzo(db, destinatario)
        sede_id = sede.id if sede else None

    segnalazione = Segnalazione(
        veicolo_id=veicolo_id,
        prenotazione_id=prenotazione_id,
        cliente_id=cliente.id if cliente else None,
        mittente_email=mittente,
        oggetto=(oggetto or "").strip()[:200] or None,
        testo=testo[:5000],
        ricevuta_il=data,
        stato="nuova",
        message_id=message_id,
        in_reply_to=in_reply_to,
        canale=canale,
        sede_id=sede_id,
    )
    db.add(segnalazione)
    db.flush()
    return segnalazione
