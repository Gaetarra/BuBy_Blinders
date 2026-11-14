"""Legge la casella di assistenza tramite l'API di Mailpit (adattatore di sviluppo).

In produzione questo modulo si sostituisce con un lettore IMAP o con un webhook di un provider,
senza toccare il resto: tutto passa da messaggi.ricevi_messaggio."""
import json
import re
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .messaggi import ricevi_messaggio
from .models import Segnalazione


def _get(percorso: str):
    with urllib.request.urlopen(f"{settings.mailpit_url}{percorso}", timeout=10) as risposta:
        return json.load(risposta)


def _indirizzo_di_casella(indirizzo: str) -> bool:
    """Vero per assistenza@dominio e per le sedi: assistenza.torino@dominio."""
    base, _, dominio = settings.inbox_address.lower().partition("@")
    locale, _, dominio_msg = indirizzo.lower().partition("@")
    return dominio_msg == dominio and (locale == base or locale.startswith(base + "."))


def _testo(dettaglio: dict) -> str:
    testo = dettaglio.get("Text") or ""
    if not testo.strip() and dettaglio.get("HTML"):
        testo = re.sub(r"<[^>]+>", " ", dettaglio["HTML"])
        testo = re.sub(r"\s+", " ", testo)
    return testo.strip()


def _data(valore: str | None) -> datetime:
    try:
        dt = datetime.fromisoformat((valore or "").replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def leggi_casella(db: Session) -> int:
    """Importa i messaggi nuovi indirizzati all'assistenza. Restituisce quanti ne ha creati."""
    nuovi = 0
    mittenti_di_sistema = {settings.mail_from.lower(), settings.inbox_address.lower()}
    for riassunto in reversed(_get("/api/v1/messages?limit=100").get("messages", [])):
        destinatari = [
            d["Address"] for d in (riassunto.get("To") or []) + (riassunto.get("Cc") or [])
        ]
        destinazione = next((d for d in destinatari if _indirizzo_di_casella(d)), None)
        mittente = (riassunto.get("From") or {}).get("Address", "")
        if destinazione is None or mittente.lower() in mittenti_di_sistema:
            continue  # non e per l'assistenza (per esempio e un'email in uscita) o e nostra
        message_id = riassunto.get("MessageID")
        if message_id and db.scalar(select(Segnalazione.id).where(Segnalazione.message_id == message_id)):
            continue

        intestazioni = {k.lower(): v for k, v in _get(f"/api/v1/message/{riassunto['ID']}/headers").items()}
        automatico = (intestazioni.get("auto-submitted") or ["no"])[0].strip().lower()
        if automatico != "no":
            continue  # risposte automatiche: si scartano per evitare cicli
        dettaglio = _get(f"/api/v1/message/{riassunto['ID']}")
        risposta_a = ((intestazioni.get("in-reply-to") or [""])[0]).strip().strip("<>") or None

        creata = ricevi_messaggio(
            db,
            mittente=mittente,
            destinatario=destinazione,
            oggetto=riassunto.get("Subject"),
            testo=_testo(dettaglio),
            data=_data(dettaglio.get("Date") or riassunto.get("Created")),
            message_id=message_id,
            in_reply_to=risposta_a,
            canale="email",
        )
        db.commit()
        if creata is not None:
            nuovi += 1
    return nuovi
