from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.import_dai import importa_cartella
from app.models import Prenotazione, Segnalazione, Veicolo


VEICOLI = """sede,citta,tipo,targa,stato,km
Torino Lingotto,Torino,auto,TEST001,disponibile,1000
Alba,Alba,ebike,EB001,disponibile,10
"""

PRENOTAZIONI = """email_cliente,nome_cliente,targa,inizio,fine,stato
cliente@example.test,Cliente Uno,TEST001,2026-11-10 09:00,2026-11-12 09:00,conclusa
"""

SEGNALAZIONI = """email_mittente,oggetto,testo,ricevuta_il,targa,categoria,urgenza,sintesi,targa_estratta
cliente@example.test,Guasto,Non parte,2026-11-11 10:00,TEST001,,,,
"""


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    with sessions() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _scrivi_cartella(cartella: Path) -> Path:
    (cartella / "veicoli.csv").write_text(VEICOLI, encoding="utf-8")
    (cartella / "prenotazioni.csv").write_text(PRENOTAZIONI, encoding="utf-8")
    (cartella / "segnalazioni.csv").write_text(SEGNALAZIONI, encoding="utf-8")
    return cartella


def test_importa_veicoli_e_prenotazioni_e_salta_segnalazioni_senza_classificazione(
    db, tmp_path
):
    esiti = importa_cartella(db, _scrivi_cartella(tmp_path))

    assert [esito.tipo for esito in esiti] == ["veicoli", "prenotazioni", "segnalazioni"]
    assert esiti[0].importate == 2
    assert esiti[1].importate == 1
    assert esiti[2].importate == 0
    assert "saltate" in esiti[2].nota
    assert len(db.scalars(select(Veicolo)).all()) == 2
    assert len(db.scalars(select(Prenotazione)).all()) == 1
    assert db.scalars(select(Segnalazione)).all() == []


def test_importa_cartella_e_rilanciabile(db, tmp_path):
    cartella = _scrivi_cartella(tmp_path)
    importa_cartella(db, cartella)
    esiti = importa_cartella(db, cartella)

    assert esiti[0].importate == 0
    assert esiti[1].importate == 0
    assert len(db.scalars(select(Veicolo)).all()) == 2
    assert len(db.scalars(select(Prenotazione)).all()) == 1


def test_segnalazioni_si_importano_solo_su_richiesta_e_segnalano_la_categoria_vuota(
    db, tmp_path
):
    esiti = importa_cartella(db, _scrivi_cartella(tmp_path), includi_segnalazioni=True)

    assert esiti[2].importate == 1
    assert "guasto" in esiti[2].nota
    segnalazione = db.scalars(select(Segnalazione)).one()
    assert segnalazione.categoria == "guasto"


def test_file_mancante_negli_obbligatori_solleva_errore(db, tmp_path):
    (tmp_path / "veicoli.csv").write_text(VEICOLI, encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="prenotazioni.csv"):
        importa_cartella(db, tmp_path)


def test_prenotazione_in_corso_imposta_veicolo_noleggiato(db, tmp_path):
    (tmp_path / "veicoli.csv").write_text(VEICOLI, encoding="utf-8")
    (tmp_path / "prenotazioni.csv").write_text(
        "email_cliente,nome_cliente,targa,inizio,fine,stato\n"
        "cliente@example.test,Cliente Uno,TEST001,2026-11-10 09:00,2026-11-12 09:00,in_corso\n",
        encoding="utf-8",
    )
    importa_cartella(db, tmp_path)
    veicolo = db.scalar(select(Veicolo).where(Veicolo.targa == "TEST001"))
    assert veicolo.stato == "noleggiato"
