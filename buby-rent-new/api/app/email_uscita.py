"""Email in uscita: accodamento (API) e invio (worker)."""
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Cliente, EmailDaInviare, Prenotazione, Segnalazione, Veicolo

MAX_TENTATIVI = 5
CORPO_RIMOSSO = "[rimosso dopo l'invio]"
ETICHETTE_STATO = {"nuova": "ricevuta", "in_lavorazione": "in lavorazione", "chiusa": "chiusa"}


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def codice_prenotazione(prenotazione_id: int) -> str:
    return f"BR-{prenotazione_id:06d}"


def codice_segnalazione(segnalazione_id: int) -> str:
    return f"SG-{segnalazione_id:06d}"


def accoda_email(db: Session, destinatario: str | None, oggetto: str, corpo: str):
    """Aggiunge l'email alla coda senza fare commit: parte (o no) insieme all'azione che la genera."""
    if not destinatario or destinatario.lower().endswith("@anonimo.invalid"):
        return None
    email = EmailDaInviare(
        destinatario=destinatario, oggetto=oggetto, corpo=corpo, creata_il=_adesso()
    )
    db.add(email)
    return email


def accoda_conferma_prenotazione(
    db: Session, prenotazione: Prenotazione, veicolo: Veicolo, cliente: Cliente
):
    codice = codice_prenotazione(prenotazione.id)
    corpo = (
        f"Gentile {cliente.nome},\n\n"
        f"la tua prenotazione {codice} e confermata.\n\n"
        f"Veicolo: {veicolo.tipo} {veicolo.targa}\n"
        f"Ritiro: {prenotazione.inizio:%d/%m/%Y %H:%M}\n"
        f"Riconsegna: {prenotazione.fine:%d/%m/%Y %H:%M}\n\n"
        f"Per segnalare un problema rispondi a questa email: l'oggetto contiene il codice {codice}.\n\n"
        "Buby Rent"
    )
    return accoda_email(db, cliente.email, f"Prenotazione {codice} confermata", corpo)


def accoda_stato_segnalazione(db: Session, segnalazione: Segnalazione):
    codice = codice_segnalazione(segnalazione.id)
    stato = ETICHETTE_STATO.get(segnalazione.stato, segnalazione.stato)
    corpo = (
        f"La tua segnalazione {codice} e ora: {stato}.\n\n"
        "Se hai altro da aggiungere rispondi a questa email.\n\nBuby Rent"
    )
    return accoda_email(db, segnalazione.mittente_email, f"Segnalazione {codice}: {stato}", corpo)


def _smtp_invia(destinatario: str, oggetto: str, corpo: str) -> None:
    messaggio = EmailMessage()
    messaggio["From"] = settings.mail_from
    messaggio["To"] = destinatario
    messaggio["Reply-To"] = settings.inbox_address
    messaggio["Subject"] = oggetto
    messaggio["Auto-Submitted"] = "auto-generated"  # evita cicli con risponditori automatici
    messaggio.set_content(corpo)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(messaggio)


def invia_coda(db: Session, limite: int = 20) -> tuple[int, int]:
    """Spedisce le email in coda. Restituisce (inviate, fallite)."""
    inviate = fallite = 0
    da_inviare = list(
        db.scalars(
            select(EmailDaInviare)
            .where(EmailDaInviare.stato == "da_inviare", EmailDaInviare.tentativi < MAX_TENTATIVI)
            .order_by(EmailDaInviare.id)
            .limit(limite)
        )
    )
    for email in da_inviare:
        try:
            _smtp_invia(email.destinatario, email.oggetto, email.corpo)
        except Exception as errore:  # noqa: BLE001 - serve registrare qualsiasi errore di rete
            email.tentativi += 1
            email.errore = type(errore).__name__  # solo il tipo: il messaggio puo contenere indirizzi
            if email.tentativi >= MAX_TENTATIVI:
                email.stato = "errore"
            fallite += 1
        else:
            email.stato = "inviata"
            email.inviata_il = _adesso()
            email.errore = None
            email.corpo = CORPO_RIMOSSO
            inviate += 1
        db.commit()
    return inviate, fallite
