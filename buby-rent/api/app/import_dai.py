"""Importa i CSV del team DAI (`dai/export_app`) nell'applicazione.

Uso:
    python -m app.import_dai /dai
    python -m app.import_dai /dai --segnalazioni

I file vanno importati nell'ordine veicoli -> prenotazioni -> segnalazioni.
Le segnalazioni sono escluse per impostazione predefinita finché la
classificazione non compila `categoria`: senza categorie l'app assegna a tutte
il valore predefinito `guasto`.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .database import Base, SessionLocal, engine
from .import_csv import IMPORTATORI, leggi_csv

CAMPI_CLASSIFICAZIONE = ("categoria", "urgenza", "sintesi", "targa_estratta")


@dataclass
class EsitoFile:
    tipo: str
    importate: int = 0
    saltate: int = 0
    nota: str = ""


def classificate(righe: list[dict[str, str]]) -> bool:
    """True se almeno una riga ha un campo di classificazione compilato."""
    return any(
        (riga.get(campo) or "").strip()
        for riga in righe
        for campo in CAMPI_CLASSIFICAZIONE
    )


def importa_cartella(
    db, cartella: str | Path, includi_segnalazioni: bool = False
) -> list[EsitoFile]:
    percorso = Path(cartella)
    esiti: list[EsitoFile] = []

    for tipo in ("veicoli", "prenotazioni"):
        file = percorso / f"{tipo}.csv"
        if not file.is_file():
            raise FileNotFoundError(f"file mancante: {file}")
        report = IMPORTATORI[tipo](db, leggi_csv(str(file)))
        esiti.append(EsitoFile(tipo, report.importate, len(report.saltate)))

    file_segnalazioni = percorso / "segnalazioni.csv"
    if not file_segnalazioni.is_file():
        esiti.append(EsitoFile("segnalazioni", nota="file assente, saltate"))
        return esiti

    righe = leggi_csv(str(file_segnalazioni))
    if not includi_segnalazioni:
        esiti.append(
            EsitoFile(
                "segnalazioni",
                nota="saltate: categoria vuota o import non richiesto (--segnalazioni)",
            )
        )
        return esiti

    report = IMPORTATORI["segnalazioni"](db, righe)
    nota = "" if classificate(righe) else "attenzione: nessuna categoria, importate come guasto"
    esiti.append(EsitoFile("segnalazioni", report.importate, len(report.saltate), nota))
    return esiti


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa veicoli e prenotazioni (e, su richiesta, segnalazioni) dai CSV DAI."
    )
    parser.add_argument("cartella", nargs="?", default="/dai", help="cartella dei CSV (default: /dai)")
    parser.add_argument(
        "--segnalazioni",
        action="store_true",
        help="importa anche segnalazioni.csv, anche se la categoria è vuota",
    )
    args = parser.parse_args()

    Base.metadata.create_all(engine)
    try:
        with SessionLocal() as db:
            esiti = importa_cartella(db, args.cartella, args.segnalazioni)
    except FileNotFoundError as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        raise SystemExit(1) from errore

    for esito in esiti:
        riga = f"{esito.tipo:<14} importate: {esito.importate:<5} saltate: {esito.saltate:<5}"
        if esito.nota:
            riga = f"{riga} {esito.nota}"
        print(riga)


if __name__ == "__main__":
    main()
