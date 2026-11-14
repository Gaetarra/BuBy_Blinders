from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .crypto import blind_index
from .database import Base
from .encrypted_types import StringaCifrata

TIPI_VEICOLO = ("auto", "furgone", "ebike")
STATI_VEICOLO = (
    "disponibile",
    "prenotato",
    "noleggiato",
    "in_manutenzione",
    "danneggiato",
    "in_trasferimento",
)
STATI_PRENOTAZIONE = ("richiesta", "confermata", "in_corso", "conclusa", "annullata")
STATI_ATTIVI = ("richiesta", "confermata", "in_corso")
STATI_NON_NOLEGGIABILI = ("in_manutenzione", "danneggiato", "in_trasferimento")
RUOLI = ("cliente", "operatore", "admin")
STATI_SEGNALAZIONE = ("nuova", "in_lavorazione", "chiusa")
CANALI = ("app", "email", "csv")
STATI_EMAIL = ("da_inviare", "inviata", "errore", "annullata")


class Sede(Base):
    __tablename__ = "sedi"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    citta: Mapped[str] = mapped_column(String(100))
    veicoli: Mapped[list["Veicolo"]] = relationship(back_populates="sede")


class Veicolo(Base):
    __tablename__ = "veicoli"
    id: Mapped[int] = mapped_column(primary_key=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedi.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    targa: Mapped[str] = mapped_column(String(20), unique=True)
    stato: Mapped[str] = mapped_column(String(20), default="disponibile")
    km: Mapped[int] = mapped_column(Integer, default=0)
    sede: Mapped[Sede] = relationship(back_populates="veicoli")


class Cliente(Base):
    """Anagrafica del cliente. Nome ed email sono cifrati nel database."""

    __tablename__ = "clienti"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), default="privato")
    nome: Mapped[str] = mapped_column(StringaCifrata)
    email: Mapped[str] = mapped_column(StringaCifrata)
    email_idx: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    anonimizzato_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @validates("email")
    def _aggiorna_indice(self, key, value):
        value = value.strip().lower()
        self.email_idx = blind_index(value)
        return value


class Prenotazione(Base):
    __tablename__ = "prenotazioni"
    id: Mapped[int] = mapped_column(primary_key=True)
    veicolo_id: Mapped[int] = mapped_column(ForeignKey("veicoli.id"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clienti.id"), index=True)
    inizio: Mapped[datetime] = mapped_column(DateTime)
    fine: Mapped[datetime] = mapped_column(DateTime)
    stato: Mapped[str] = mapped_column(String(20), default="confermata")


class Utente(Base):
    __tablename__ = "utenti"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(StringaCifrata)
    email_idx: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    ruolo: Mapped[str] = mapped_column(String(20), default="cliente")
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clienti.id"), nullable=True)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedi.id"), nullable=True)
    privacy_versione: Mapped[str | None] = mapped_column(String(20), nullable=True)
    privacy_accettata_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @validates("email")
    def _aggiorna_indice(self, key, value):
        value = value.strip().lower()
        self.email_idx = blind_index(value)
        return value


class Segnalazione(Base):
    """Segnalazione o richiesta di assistenza. Mittente, oggetto, testo e sintesi sono cifrati."""

    __tablename__ = "segnalazioni"
    id: Mapped[int] = mapped_column(primary_key=True)
    veicolo_id: Mapped[int | None] = mapped_column(ForeignKey("veicoli.id"), nullable=True, index=True)
    prenotazione_id: Mapped[int | None] = mapped_column(ForeignKey("prenotazioni.id"), nullable=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clienti.id"), nullable=True, index=True)
    mittente_email: Mapped[str | None] = mapped_column(StringaCifrata, nullable=True)
    oggetto: Mapped[str | None] = mapped_column(StringaCifrata, nullable=True)
    testo: Mapped[str] = mapped_column(StringaCifrata)
    ricevuta_il: Mapped[datetime] = mapped_column(DateTime, index=True)
    stato: Mapped[str] = mapped_column(String(20), default="nuova", index=True)
    # compilati dal team DAI (classificazione ed estrazione)
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    urgenza: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sintesi: Mapped[str | None] = mapped_column(StringaCifrata, nullable=True)
    targa_estratta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # provenienza e gestione
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canale: Mapped[str] = mapped_column(String(20), default="app")
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedi.id"), nullable=True, index=True)
    assegnata_a: Mapped[int | None] = mapped_column(ForeignKey("utenti.id"), nullable=True, index=True)


class NotaInterna(Base):
    """Nota interna su una segnalazione: mai visibile al cliente. Testo cifrato."""

    __tablename__ = "note_interne"
    id: Mapped[int] = mapped_column(primary_key=True)
    segnalazione_id: Mapped[int] = mapped_column(ForeignKey("segnalazioni.id"), index=True)
    autore_id: Mapped[int] = mapped_column(ForeignKey("utenti.id"))
    testo: Mapped[str] = mapped_column(StringaCifrata)
    creata_il: Mapped[datetime] = mapped_column(DateTime)


class EmailDaInviare(Base):
    """Coda delle email in uscita (outbox). L'API accoda nella stessa transazione dell'azione,
    il worker spedisce. Dopo l'invio il corpo viene rimosso."""

    __tablename__ = "email_da_inviare"
    id: Mapped[int] = mapped_column(primary_key=True)
    destinatario: Mapped[str] = mapped_column(StringaCifrata)
    destinatario_idx: Mapped[str] = mapped_column(String(64), index=True)
    oggetto: Mapped[str] = mapped_column(StringaCifrata)
    corpo: Mapped[str] = mapped_column(StringaCifrata)
    stato: Mapped[str] = mapped_column(String(20), default="da_inviare", index=True)
    tentativi: Mapped[int] = mapped_column(Integer, default=0)
    errore: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creata_il: Mapped[datetime] = mapped_column(DateTime)
    inviata_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @validates("destinatario")
    def _aggiorna_indice(self, key, value):
        value = value.strip().lower()
        self.destinatario_idx = blind_index(value)
        return value
