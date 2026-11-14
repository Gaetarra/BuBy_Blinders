from pathlib import Path

from app import import_csv as imp
from app.models import Prenotazione, Segnalazione, Veicolo

DATA = Path(__file__).resolve().parents[2] / "data"


def _importa(db, tipo, nome):
    return imp.IMPORTATORI[tipo](db, imp.leggi_csv(str(DATA / nome)))


def test_import_completo_e_idempotente(client, db):
    assert _importa(db, "veicoli", "esempio_veicoli.csv").importate == 2        # la moto e scartata
    r = _importa(db, "prenotazioni", "esempio_prenotazioni.csv")
    assert r.importate == 3 and len(r.saltate) == 3
    r = _importa(db, "segnalazioni", "esempio_segnalazioni.csv")
    assert r.importate == 2 and len(r.saltate) == 1

    for tipo, nome in (("veicoli", "esempio_veicoli.csv"), ("prenotazioni", "esempio_prenotazioni.csv"), ("segnalazioni", "esempio_segnalazioni.csv")):
        assert _importa(db, tipo, nome).importate == 0                          # rilancio: nessun duplicato
    assert db.query(Prenotazione).count() == 3 and db.query(Segnalazione).count() == 2

    s = db.query(Segnalazione).filter(Segnalazione.targa_estratta == "EB001XX").one()
    assert s.canale == "csv" and s.veicolo_id == db.query(Veicolo).filter(Veicolo.targa == "EB001XX").one().id
    assert s.sede_id is not None
