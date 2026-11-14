"""Ricifra i dati personali con la chiave primaria corrente.

Procedura di rotazione:
1. genera una nuova chiave Fernet
2. mettila PRIMA delle altre in ENCRYPTION_KEYS (NUOVA,VECCHIA) e riavvia l'API
3. esegui:  docker compose exec api python -m app.rotate_keys
4. quando il comando termina, togli la chiave vecchia da ENCRYPTION_KEYS
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .database import SessionLocal
from .models import Cliente, Utente

CAMPI_CIFRATI = ((Cliente, ("nome", "email")), (Utente, ("email",)))


def ruota(db: Session) -> int:
    righe = 0
    for modello, campi in CAMPI_CIFRATI:
        for riga in db.scalars(select(modello)):
            for campo in campi:
                flag_modified(riga, campo)  # forza la riscrittura, cifrata con la chiave primaria
            righe += 1
    db.commit()
    return righe


if __name__ == "__main__":
    with SessionLocal() as sessione:
        print(f"Righe ricifrate: {ruota(sessione)}")
