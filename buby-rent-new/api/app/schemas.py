from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import STATI_SEGNALAZIONE, STATI_VEICOLO

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


class SegnalazioneIn(BaseModel):
    veicolo_id: int | None = None
    prenotazione_id: int | None = None
    cliente_id: int | None = Field(default=None, description="Solo per operatori e admin")
    oggetto: str | None = Field(default=None, max_length=200)
    testo: str = Field(min_length=1, max_length=5000)


class SegnalazioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    veicolo_id: int | None
    prenotazione_id: int | None
    cliente_id: int | None
    mittente_email: str | None
    oggetto: str | None
    testo: str
    ricevuta_il: datetime
    stato: str
    categoria: str | None
    urgenza: str | None
    sintesi: str | None
    targa_estratta: str | None
    canale: str
    sede_id: int | None
    assegnata_a: int | None


class SegnalazioneAggiorna(BaseModel):
    stato: str | None = None
    categoria: str | None = Field(default=None, max_length=50)
    urgenza: str | None = Field(default=None, max_length=20)
    assegnata_a: int | None = Field(default=None, description="id di un operatore o admin; null per togliere l'assegnazione")

    @field_validator("stato")
    @classmethod
    def stato_valido(cls, v):
        if v is not None and v not in STATI_SEGNALAZIONE:
            raise ValueError(f"stato non valido, usa uno tra: {', '.join(STATI_SEGNALAZIONE)}")
        return v


class EsportazioneDati(BaseModel):
    """Copia dei dati personali dell'utente (diritto di accesso e portabilita)."""

    utente: UtenteOut
    privacy_versione: str | None
    privacy_accettata_il: datetime | None
    cliente: ClienteDati | None
    prenotazioni: list[PrenotazioneOut]
    segnalazioni: list[SegnalazioneOut]


class NotaIn(BaseModel):
    testo: str = Field(min_length=1, max_length=2000)


class NotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    segnalazione_id: int
    autore_id: int
    testo: str
    creata_il: datetime
