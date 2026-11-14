"""Importa veicoli, prenotazioni e segnalazioni da CSV rilanciabili."""

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

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
FORMATO_DATE = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M")


@dataclass
class Report:
    importate: int = 0
    saltate: list[tuple[int, str]] = field(default_factory=list)


def leggi_csv(percorso: str) -> list[dict[str, str]]:
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        righe = file.read().splitlines()
    if not righe:
        return []
    delimitatore = ";" if righe[0].count(";") > righe[0].count(",") else ","
    return [
        {(chiave or "").strip().lower(): (valore or "").strip() for chiave, valore in riga.items()}
        for riga in csv.DictReader(righe, delimiter=delimitatore)
    ]


def _obbligatorio(riga: dict[str, str], campo: str) -> str:
    valore = riga.get(campo, "")
    if not valore:
        raise ValueError(f"campo obbligatorio mancante: {campo}")
    return valore


def _data(valore: str) -> datetime:
    try:
        data = datetime.fromisoformat(valore)
    except ValueError:
        for formato in FORMATO_DATE:
            try:
                data = datetime.strptime(valore, formato)
                break
            except ValueError:
                continue
        else:
            raise ValueError("data non valida")
    return (
        data.astimezone(timezone.utc).replace(tzinfo=None)
        if data.tzinfo
        else data
    )


def _per_riga(db, righe, funzione) -> Report:
    report = Report()
    for numero, riga in enumerate(righe, start=2):
        try:
            if funzione(riga):
                report.importate += 1
            else:
                report.saltate.append((numero, "gia presente"))
        except ValueError as errore:
            report.saltate.append((numero, str(errore)))
    db.commit()
    return report


def importa_veicoli(db, righe) -> Report:
    def importa(riga):
        targa = _obbligatorio(riga, "targa").upper()
        tipo = _obbligatorio(riga, "tipo").lower()
        stato = (riga.get("stato") or "disponibile").lower()
        if tipo not in TIPI_VEICOLO or stato not in STATI_VEICOLO:
            raise ValueError("tipo o stato non valido")
        if db.scalar(select(Veicolo.id).where(Veicolo.targa == targa)):
            return False
        sede_nome = _obbligatorio(riga, "sede")
        sede = db.scalar(select(Sede).where(Sede.nome == sede_nome))
        if sede is None:
            sede = Sede(nome=sede_nome, citta=riga.get("citta") or sede_nome)
            db.add(sede)
            db.flush()
        db.add(
            Veicolo(
                sede_id=sede.id,
                tipo=tipo,
                targa=targa,
                stato=stato,
                km=int(riga.get("km") or 0),
            )
        )
        db.flush()
        return True

    return _per_riga(db, righe, importa)


def importa_prenotazioni(db, righe) -> Report:
    def importa(riga):
        email = _obbligatorio(riga, "email_cliente").lower()
        if not EMAIL.match(email):
            raise ValueError("email non valida")
        targa = _obbligatorio(riga, "targa").upper()
        inizio, fine = _data(_obbligatorio(riga, "inizio")), _data(_obbligatorio(riga, "fine"))
        stato = (riga.get("stato") or "conclusa").lower()
        veicolo = db.scalar(select(Veicolo).where(Veicolo.targa == targa))
        if veicolo is None:
            raise ValueError("veicolo non trovato")
        if fine <= inizio or stato not in STATI_PRENOTAZIONE:
            raise ValueError("date o stato non validi")
        if stato in STATI_ATTIVI and db.scalar(
            select(ha_sovrapposizioni(veicolo.id, inizio, fine))
        ):
            raise ValueError("sovrapposizione con prenotazione attiva")
        cliente = db.scalar(select(Cliente).where(Cliente.email_idx == blind_index(email)))
        if cliente is None:
            cliente = Cliente(
                tipo="privato",
                nome=riga.get("nome_cliente") or "Cliente importato",
                email=email,
            )
            db.add(cliente)
            db.flush()
        esistente = db.scalar(
            select(Prenotazione.id).where(
                Prenotazione.veicolo_id == veicolo.id,
                Prenotazione.cliente_id == cliente.id,
                Prenotazione.inizio == inizio,
                Prenotazione.fine == fine,
            )
        )
        if esistente:
            return False
        db.add(
            Prenotazione(
                veicolo_id=veicolo.id,
                cliente_id=cliente.id,
                inizio=inizio,
                fine=fine,
                stato=stato,
            )
        )
        return True

    return _per_riga(db, righe, importa)


def importa_segnalazioni(db, righe) -> Report:
    def importa(riga):
        email = _obbligatorio(riga, "email_mittente").lower()
        testo = _obbligatorio(riga, "testo")
        targa = _obbligatorio(riga, "targa").upper()
        ricevuta = _data(_obbligatorio(riga, "ricevuta_il"))
        veicolo = db.scalar(select(Veicolo).where(Veicolo.targa == targa))
        if veicolo is None:
            raise ValueError("veicolo non trovato")
        cliente = db.scalar(select(Cliente).where(Cliente.email_idx == blind_index(email)))
        duplicato = db.scalar(
            select(Segnalazione.id).where(
                Segnalazione.veicolo_id == veicolo.id,
                Segnalazione.testo == testo,
                Segnalazione.creato_il == ricevuta,
            )
        )
        if duplicato:
            return False
        db.add(
            Segnalazione(
                veicolo_id=veicolo.id,
                cliente_id=cliente.id if cliente else None,
                categoria=(riga.get("categoria") or "guasto")[:30],
                testo=testo[:1000],
                creato_il=ricevuta,
            )
        )
        return True

    return _per_riga(db, righe, importa)


IMPORTATORI = {
    "veicoli": importa_veicoli,
    "prenotazioni": importa_prenotazioni,
    "segnalazioni": importa_segnalazioni,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tipo", choices=IMPORTATORI)
    parser.add_argument("file")
    args = parser.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        report = IMPORTATORI[args.tipo](db, leggi_csv(args.file))
    print(f"Importate: {report.importate}  Saltate: {len(report.saltate)}")
    for numero, motivo in report.saltate[:30]:
        print(f"  riga {numero}: {motivo}")


if __name__ == "__main__":
    main()
