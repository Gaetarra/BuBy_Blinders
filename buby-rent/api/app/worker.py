"""Worker per la coda email.

Avvio: ``python -m app.worker``.
"""

from datetime import datetime, timezone
from email.message import EmailMessage
import logging
import smtplib
import time

from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import EmailDaInviare

log = logging.getLogger("buby.worker")


def _adesso():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def invia_coda() -> None:
    with SessionLocal() as db:
        messaggi = list(
            db.scalars(
                select(EmailDaInviare)
                .where(
                    EmailDaInviare.stato == "da_inviare",
                    EmailDaInviare.tentativi < 5,
                )
                .order_by(EmailDaInviare.id)
                .limit(20)
            )
        )
        for messaggio in messaggi:
            messaggio.tentativi += 1
            try:
                contenuto = EmailMessage()
                contenuto["From"] = settings.mail_from
                contenuto["To"] = messaggio.destinatario
                contenuto["Subject"] = messaggio.oggetto
                contenuto.set_content(messaggio.corpo or "")
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                    if settings.smtp_starttls:
                        smtp.starttls()
                    if settings.smtp_user:
                        smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(contenuto)
                messaggio.stato = "inviata"
                messaggio.inviata_il = _adesso()
                messaggio.corpo = None
            except (OSError, smtplib.SMTPException) as errore:
                messaggio.errore = type(errore).__name__
                if messaggio.tentativi >= 5:
                    messaggio.stato = "errore"
            db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    log.info("worker avviato")
    while True:
        invia_coda()
        time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
