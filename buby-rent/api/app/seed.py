from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Cliente, Sede, Utente, Veicolo
from .security import hash_password


def carica_dati_mock(db: Session) -> None:
    """Dati di prova, finche il team DAI non consegna quelli reali."""
    if db.scalar(select(Sede.id).limit(1)) is None:
        sedi = [
            Sede(nome="Torino Centro", citta="Torino"),
            Sede(nome="Lago Maggiore", citta="Stresa"),
        ]
        db.add_all(sedi)
        db.flush()
        veicoli = []
        for sede in sedi:
            for i, tipo in enumerate(["auto", "auto", "furgone", "ebike", "ebike"]):
                veicoli.append(
                    Veicolo(sede_id=sede.id, tipo=tipo, targa=f"MOCK{sede.id}{i:02d}", km=1000 * i)
                )
        db.add_all(veicoli)
        db.add(Cliente(tipo="privato", nome="Mario Rossi", email="mario@example.com"))
        db.commit()

    if db.scalar(select(Utente.id).limit(1)) is None:
        prima_sede = db.scalar(select(Sede.id).order_by(Sede.id).limit(1))
        db.add_all(
            [
                Utente(
                    email=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                    ruolo="admin",
                ),
                Utente(
                    email="operatore@buby.it",
                    password_hash=hash_password(settings.operatore_password),
                    ruolo="operatore",
                    sede_id=prima_sede,
                ),
            ]
        )
        db.commit()
