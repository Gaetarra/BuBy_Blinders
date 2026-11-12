from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .crypto import blind_index
from .database import Base
from .encrypted_types import StringaCifrata


def _adesso_utc_senza_fuso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
STATI_MANUTENZIONE = ("programmata", "in_corso", "completata", "annullata")
STATI_TRASFERIMENTO = ("programmato", "in_corso", "completato", "annullato")
FASE_ISPEZIONE = ("ritiro", "riconsegna")
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
    segnalazioni: Mapped[list["Segnalazione"]] = relationship(back_populates="veicolo")
    manutenzioni: Mapped[list["Manutenzione"]] = relationship(back_populates="veicolo")
    trasferimenti: Mapped[list["Trasferimento"]] = relationship(back_populates="veicolo")


class Cliente(Base):
    """Anagrafica del cliente. Nome ed email sono cifrati nel database."""

    __tablename__ = "clienti"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), default="privato")
    nome: Mapped[str] = mapped_column(StringaCifrata)
    email: Mapped[str] = mapped_column(StringaCifrata)
    email_idx: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    anonimizzato_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    segnalazioni: Mapped[list["Segnalazione"]] = relationship(back_populates="cliente")

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
    ispezioni: Mapped[list["Ispezione"]] = relationship(back_populates="prenotazione")


class Ispezione(Base):
    __tablename__ = "ispezioni"
    id: Mapped[int] = mapped_column(primary_key=True)
    prenotazione_id: Mapped[int] = mapped_column(ForeignKey("prenotazioni.id"), index=True)
    fase: Mapped[str] = mapped_column(String(20), default="ritiro")
    km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carburante: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batteria: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=_adesso_utc_senza_fuso)
    prenotazione: Mapped[Prenotazione] = relationship(back_populates="ispezioni")


class Segnalazione(Base):
    __tablename__ = "segnalazioni"
    id: Mapped[int] = mapped_column(primary_key=True)
    veicolo_id: Mapped[int] = mapped_column(ForeignKey("veicoli.id"), index=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clienti.id"), nullable=True, index=True)
    categoria: Mapped[str] = mapped_column(String(30), default="guasto")
    testo: Mapped[str] = mapped_column(String(1000))
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=_adesso_utc_senza_fuso)
    veicolo: Mapped[Veicolo] = relationship(back_populates="segnalazioni")
    cliente: Mapped[Cliente | None] = relationship(back_populates="segnalazioni")


class Manutenzione(Base):
    __tablename__ = "manutenzioni"
    id: Mapped[int] = mapped_column(primary_key=True)
    veicolo_id: Mapped[int] = mapped_column(ForeignKey("veicoli.id"), index=True)
    descrizione: Mapped[str] = mapped_column(String(500))
    stato: Mapped[str] = mapped_column(String(20), default="programmata")
    inizio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fine: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    veicolo: Mapped[Veicolo] = relationship(back_populates="manutenzioni")


class Trasferimento(Base):
    __tablename__ = "trasferimenti"
    id: Mapped[int] = mapped_column(primary_key=True)
    veicolo_id: Mapped[int] = mapped_column(ForeignKey("veicoli.id"), index=True)
    sede_origine_id: Mapped[int] = mapped_column(ForeignKey("sedi.id"), index=True)
    sede_destinazione_id: Mapped[int] = mapped_column(ForeignKey("sedi.id"), index=True)
    inizio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fine: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stato: Mapped[str] = mapped_column(String(20), default="programmato")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    veicolo: Mapped[Veicolo] = relationship(back_populates="trasferimenti")


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


class IdentitaSupabase(Base):
    __tablename__ = "identita_supabase"
    supabase_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    utente_id: Mapped[int] = mapped_column(
        ForeignKey("utenti.id"), unique=True, index=True
    )
    collegato_il: Mapped[datetime] = mapped_column(DateTime, default=_adesso_utc_senza_fuso)
