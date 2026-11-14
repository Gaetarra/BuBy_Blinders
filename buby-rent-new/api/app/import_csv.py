"""Importa dati da CSV (veicoli, prenotazioni, segnalazioni) nel database.

Uso (con Docker):
    docker compose exec api python -m app.import_csv veicoli /data/veicoli.csv
    docker compose exec api python -m app.import_csv prenotazioni /data/prenotazioni.csv
    docker compose exec api python -m app.import_csv segnalazioni /data/segnalazioni.csv

Si scrive passando dai modelli, quindi i campi personali vengono cifrati in automatico.
L'import si puo rilanciare: le righe gia presenti vengono saltate.
Separatore , oppure ; (rilevato in automatico). Date: ISO (2026-09-01 09:00) o 01/09/2026 09:00.
"""
import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .availability import ha_sovrapposizioni
from .crypto import blind_index
from .database import Base, SessionLocal, engine
from .models import (
    STATI_ATTIVI,
    STATI_PRENOTAZIONE,
    STATI_VEICOLO,
    TIPI_VEICOLO,
    Cliente,
    Prenotazione,
    Sede,
    Segnalazione,
    Veicolo,
)

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORMATI_DATA = ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y")


@dataclass
class Report:
    importate: int = 0
    saltate: list[tuple[int, str]] = field(default_factory=list)


def leggi_csv(percorso: str) -> list[dict]:
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        contenuto = f.read()
    prima_riga = contenuto.splitlines()[0] if contenuto else ""
    separatore = ";" if prima_riga.count(";") > prima_riga.count(",") else ","
    lettore = csv.DictReader(contenuto.splitlines(), delimiter=separatore)
    righe = []
    for riga in lettore:
        righe.append({(k or "").strip().lower(): (v or "").strip() for k, v in riga.items()})
    return righe


def _data(valore: str) -> datetime:
    valore = valore.strip()
    try:
        dt = datetime.fromisoformat(valore)
    except ValueError:
        for formato in FORMATI_DATA:
            try:
                dt = datetime.strptime(valore, formato)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"data non valida: '{valore}'")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _obbligatorio(riga: dict, campo: str) -> str:
    valore = riga.get(campo, "")
    if not valore:
        raise ValueError(f"campo obbligatorio mancante: {campo}")
    return valore


def _email(valore: str) -> str:
    if not EMAIL.match(valore):
        raise ValueError(f"email non valida: '{valore}'")
    return valore


def _limite(valore: str, campo: str, massimo: int) -> str:
    if len(valore) > massimo:
        raise ValueError(f"{campo} troppo lungo (massimo {massimo} caratteri)")
    return valore


def _per_ogni_riga(db: Session, righe: list[dict], elabora) -> Report:
    report = Report()
    for numero, riga in enumerate(righe, start=2):  # la riga 1 e l'intestazione
        try:
            if elabora(riga):
                report.importate += 1
            else:
                report.saltate.append((numero, "gia presente"))
        except ValueError as errore:
            report.saltate.append((numero, str(errore)))
    db.commit()
    return report


def importa_veicoli(db: Session, righe: list[dict]) -> Report:
    def elabora(r: dict) -> bool:
        targa = _limite(_obbligatorio(r, "targa").upper(), "targa", 20)
        tipo = _obbligatorio(r, "tipo").lower()
        if tipo not in TIPI_VEICOLO:
            raise ValueError(f"tipo non valido '{tipo}' (ammessi: {', '.join(TIPI_VEICOLO)})")
        stato = (r.get("stato") or "disponibile").lower()
        if stato not in STATI_VEICOLO:
            raise ValueError(f"stato non valido '{stato}'")
        km = r.get("km") or "0"
        if not km.isdigit():
            raise ValueError(f"km non valido: '{km}'")
        if db.scalar(select(Veicolo.id).where(Veicolo.targa == targa)):
            return False
        nome_sede = _limite(_obbligatorio(r, "sede"), "sede", 100)
        sede = db.scalar(select(Sede).where(Sede.nome == nome_sede))
        if sede is None:
            sede = Sede(nome=nome_sede, citta=_limite(r.get("citta") or nome_sede, "citta", 100))
            db.add(sede)
            db.flush()
        db.add(Veicolo(sede_id=sede.id, tipo=tipo, targa=targa, stato=stato, km=int(km)))
        db.flush()
        return True

    return _per_ogni_riga(db, righe, elabora)


def importa_prenotazioni(db: Session, righe: list[dict]) -> Report:
    clienti: dict[str, Cliente] = {}  # cache dell'esecuzione, per impronta dell'email

    def cliente_da_email(email: str, nome: str) -> Cliente:
        indice = blind_index(email)
        if indice not in clienti:
            cliente = db.scalar(select(Cliente).where(Cliente.email_idx == indice))
            if cliente is None:
                cliente = Cliente(tipo="privato", nome=nome or "Cliente importato", email=email)
                db.add(cliente)
                db.flush()
            clienti[indice] = cliente
        return clienti[indice]

    def elabora(r: dict) -> bool:
        email = _email(_obbligatorio(r, "email_cliente"))
        targa = _obbligatorio(r, "targa").upper()
        inizio, fine = _data(_obbligatorio(r, "inizio")), _data(_obbligatorio(r, "fine"))
        if fine <= inizio:
            raise ValueError("fine non successiva a inizio")
        stato = (r.get("stato") or "conclusa").lower()
        if stato not in STATI_PRENOTAZIONE:
            raise ValueError(f"stato non valido '{stato}'")
        veicolo = db.scalar(select(Veicolo).where(Veicolo.targa == targa))
        if veicolo is None:
            raise ValueError(f"veicolo con targa {targa} non trovato (importa prima i veicoli)")
        if stato in STATI_ATTIVI and db.scalar(select(ha_sovrapposizioni(veicolo.id, inizio, fine))):
            raise ValueError("si sovrappone a un'altra prenotazione attiva dello stesso veicolo")
        cliente = cliente_da_email(email, r.get("nome_cliente", ""))
        gia = db.scalar(
            select(Prenotazione.id).where(
                Prenotazione.veicolo_id == veicolo.id,
                Prenotazione.cliente_id == cliente.id,
                Prenotazione.inizio == inizio,
                Prenotazione.fine == fine,
            )
        )
        if gia:
            return False
        db.add(
            Prenotazione(
                veicolo_id=veicolo.id, cliente_id=cliente.id, inizio=inizio, fine=fine, stato=stato
            )
        )
        db.flush()
        return True

    return _per_ogni_riga(db, righe, elabora)


def importa_segnalazioni(db: Session, righe: list[dict]) -> Report:
    def elabora(r: dict) -> bool:
        email = _email(_obbligatorio(r, "email_mittente"))
        testo = _obbligatorio(r, "testo")
        _limite(testo, "testo", 5000)
        ricevuta_il = _data(_obbligatorio(r, "ricevuta_il"))
        oggetto = _limite(r.get("oggetto", ""), "oggetto", 200) or None
        categoria = _limite(r.get("categoria", ""), "categoria", 50) or None
        urgenza = _limite(r.get("urgenza", ""), "urgenza", 20).lower() or None
        targa_estratta = _limite(r.get("targa_estratta", "").upper(), "targa_estratta", 20) or None
        stato = (r.get("stato") or "nuova").lower()

        for esistente in db.scalars(select(Segnalazione).where(Segnalazione.ricevuta_il == ricevuta_il)):
            if esistente.testo == testo:
                return False

        targa = (r.get("targa") or "").upper() or targa_estratta
        veicolo = db.scalar(select(Veicolo).where(Veicolo.targa == targa)) if targa else None
        cliente = db.scalar(select(Cliente).where(Cliente.email_idx == blind_index(email)))
        db.add(
            Segnalazione(
                veicolo_id=veicolo.id if veicolo else None,
                cliente_id=cliente.id if cliente else None,
                mittente_email=email,
                oggetto=oggetto,
                testo=testo,
                ricevuta_il=ricevuta_il,
                stato=stato,
                canale="csv",
                sede_id=veicolo.sede_id if veicolo else None,
                categoria=categoria,
                urgenza=urgenza,
                sintesi=r.get("sintesi") or None,
                targa_estratta=targa_estratta,
            )
        )
        db.flush()
        return True

    return _per_ogni_riga(db, righe, elabora)


IMPORTATORI = {
    "veicoli": importa_veicoli,
    "prenotazioni": importa_prenotazioni,
    "segnalazioni": importa_segnalazioni,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa un CSV nel database")
    parser.add_argument("tipo", choices=IMPORTATORI)
    parser.add_argument("file")
    argomenti = parser.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        report = IMPORTATORI[argomenti.tipo](db, leggi_csv(argomenti.file))
    print(f"Importate: {report.importate}  Saltate: {len(report.saltate)}")
    for riga, motivo in report.saltate[:30]:
        print(f"  riga {riga}: {motivo}")
    if len(report.saltate) > 30:
        print(f"  ... e altre {len(report.saltate) - 30}")


if __name__ == "__main__":
    main()
