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
