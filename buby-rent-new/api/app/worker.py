"""Worker: spedisce le email in coda e legge la casella di assistenza, a intervalli regolari.

Avvio:  python -m app.worker   (in Docker e il servizio `worker`)"""
import logging
import time

from .casella import leggi_casella
from .database import SessionLocal
from .email_uscita import invia_coda
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


def un_giro() -> None:
    """Un giro di lavoro. Le due fasi sono indipendenti: se la casella non risponde le email
    in coda partono lo stesso, e viceversa."""
    inviate = fallite = nuove = 0
    errori = []
    with SessionLocal() as db:
        try:
            inviate, fallite = invia_coda(db)
        except Exception as errore:  # noqa: BLE001
            db.rollback()
            errori.append(f"invio: {type(errore).__name__}")
        try:
            nuove = leggi_casella(db)
        except Exception as errore:  # noqa: BLE001
            db.rollback()
            errori.append(f"casella: {type(errore).__name__}")
    if inviate or fallite or nuove or errori:
        # nei log solo conteggi e tipi di errore, mai indirizzi o testi
        log.info("inviate: %s, fallite: %s, nuove: %s, errori: %s", inviate, fallite, nuove, errori or "nessuno")


def main() -> None:
    log.info("worker avviato (intervallo %ss)", settings.poll_seconds)
    while True:
        try:
            un_giro()
        except Exception:  # noqa: BLE001 - il worker non deve fermarsi (es. database non ancora pronto)
            log.exception("giro fallito, riprovo")
        time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
