from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import FASE_ISPEZIONE, STATI_MANUTENZIONE, STATI_TRASFERIMENTO, STATI_VEICOLO

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class VeicoloOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sede_id: int
    tipo: str
    targa: str
    stato: str
    km: int


class StatoIn(BaseModel):
    stato: str

    @field_validator("stato")
    @classmethod
    def stato_valido(cls, v: str) -> str:
        if v not in STATI_VEICOLO:
            raise ValueError(f"stato non valido, usa uno tra: {', '.join(STATI_VEICOLO)}")
        return v


class PrenotazioneIn(BaseModel):
    veicolo_id: int
    cliente_id: int | None = Field(
        default=None, description="Solo per operatori e admin; per i clienti e ricavato dal token"
    )
    inizio: datetime
    fine: datetime

    @model_validator(mode="after")
    def controlla_date(self):
        if self.fine <= self.inizio:
            raise ValueError("fine deve essere successiva a inizio")
        return self


class PrenotazioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    veicolo_id: int
    cliente_id: int
    inizio: datetime
    fine: datetime
    stato: str


class IspezioneIn(BaseModel):
    fase: str = Field(default="ritiro")
    km: int | None = Field(default=None, ge=0)
    carburante: int | None = Field(default=None, ge=0, le=100)
    batteria: int | None = Field(default=None, ge=0, le=100)
    foto_url: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=500)
    danni_rilevati: bool = False

    @field_validator("fase")
    @classmethod
    def fase_valida(cls, v: str) -> str:
        if v not in FASE_ISPEZIONE:
            raise ValueError(f"fase non valida, usa uno tra: {', '.join(FASE_ISPEZIONE)}")
        return v


class IspezioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    prenotazione_id: int
    fase: str
    km: int | None
    carburante: int | None
    batteria: int | None
    foto_url: str | None
    note: str | None
    creato_il: datetime


class SegnalazioneIn(BaseModel):
    categoria: str = Field(default="guasto", min_length=1, max_length=30)
    testo: str = Field(min_length=1, max_length=1000)


class SegnalazioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    veicolo_id: int
    cliente_id: int | None
    categoria: str
    testo: str
    creato_il: datetime


class ManutenzioneIn(BaseModel):
    descrizione: str = Field(min_length=1, max_length=500)
    stato: str = Field(default="programmata")
    inizio: datetime | None = None
    fine: datetime | None = None

    @field_validator("stato")
    @classmethod
    def stato_valido(cls, v: str) -> str:
        if v not in STATI_MANUTENZIONE:
            raise ValueError(f"stato non valido, usa uno tra: {', '.join(STATI_MANUTENZIONE)}")
        return v


class ManutenzioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    veicolo_id: int
    descrizione: str
    stato: str
    inizio: datetime | None
    fine: datetime | None


class TrasferimentoIn(BaseModel):
    sede_destinazione_id: int
    inizio: datetime | None = None
    fine: datetime | None = None
    stato: str = Field(default="programmato")
    note: str | None = Field(default=None, max_length=500)

    @field_validator("stato")
    @classmethod
    def stato_valido(cls, v: str) -> str:
        if v not in STATI_TRASFERIMENTO:
            raise ValueError(f"stato non valido, usa uno tra: {', '.join(STATI_TRASFERIMENTO)}")
        return v


class TrasferimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    veicolo_id: int
    sede_origine_id: int
    sede_destinazione_id: int
    inizio: datetime | None
    fine: datetime | None
    stato: str
    note: str | None


class DashboardFlottaOut(BaseModel):
    sede_id: int
    veicoli_totali: int
    veicoli_per_stato: dict[str, int]
    veicoli: list[VeicoloOut]
    prenotazioni: list[PrenotazioneOut]


class ClienteRiferimento(BaseModel):
    id: int


class CollegamentoSupabaseIn(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    tipo: str = Field(default="privato", pattern="^(privato|azienda)$")
    accetta_privacy: bool = False


class CheckInOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stato: str
    veicolo_id: int
    foto_url: str | None = None
    note: str | None = None


class RegistrazioneIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=150)
    password: str = Field(min_length=8, max_length=72)
    tipo: str = Field(default="privato", pattern="^(privato|azienda)$")
    accetta_privacy: bool = Field(description="Presa visione dell'informativa privacy")

    @field_validator("accetta_privacy")
    @classmethod
    def privacy_accettata(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Per registrarti devi accettare l'informativa privacy")
        return v


class UtenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    ruolo: str
    cliente_id: int | None
    sede_id: int | None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AggiornaProfiloIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)


class ClienteDati(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: str
    nome: str
    email: str


class EsportazioneDati(BaseModel):
    """Copia dei dati personali dell'utente (diritto di accesso e portabilita)."""

    utente: UtenteOut
    privacy_versione: str | None
    privacy_accettata_il: datetime | None
    cliente: ClienteDati | None
    prenotazioni: list[PrenotazioneOut]
