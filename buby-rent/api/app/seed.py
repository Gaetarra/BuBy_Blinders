from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .crypto import blind_index
from .models import (
    Cliente,
    Manutenzione,
    Prenotazione,
    Segnalazione,
    Sede,
    Utente,
    Veicolo,
)
from .security import hash_password

# Le sedi coincidono con quelle dei dati del team DAI (`dai/export_app`), così
# l'import dei CSV non crea sedi doppie.
SEDI_DEMO = [
    ("Torino Lingotto", "Torino"),
    ("Alba", "Alba"),
    ("Bardonecchia", "Bardonecchia"),
    ("Stresa", "Stresa"),
    ("Casale Monferrato", "Casale Monferrato"),
]

OPERATORI_DEMO = {
    "Torino Lingotto": "operatore.lingotto@buby.it",
    "Alba": "operatore.alba@buby.it",
    "Bardonecchia": "operatore.bardonecchia@buby.it",
    "Stresa": "operatore.stresa@buby.it",
    "Casale Monferrato": "operatore.casale-monferrato@buby.it",
}

CONFIGURAZIONE_FLOTTA = [
    ("auto", "TO"),
    ("auto", "TO"),
    ("furgone", "TO"),
    ("ebike", "EB"),
    ("auto", "TO"),
    ("ebike", "EB"),
    ("auto", "TO"),
    ("furgone", "TO"),
]

STATI_FLOTTA = [
    "disponibile",
    "prenotato",
    "noleggiato",
    "in_manutenzione",
    "disponibile",
    "danneggiato",
    "disponibile",
    "in_trasferimento",
]

NOMI_CLIENTI = [
    "Giulia Ferrero",
    "Luca Rinaldi",
    "Marta Gallo",
    "Officine Dora",
    "Andrea Serra",
    "Elisa Marino",
    "Paolo Rossetti",
    "Studio Mole",
    "Chiara Costa",
    "Davide Bruno",
    "Sara Villa",
    "Logistica Po",
]


def _carica_flotta_demo(db: Session, sedi: list[Sede]) -> None:
    veicoli = [
        Veicolo(
            sede_id=sede.id,
            tipo=tipo,
            targa=f"{targa}-{sede.id}{indice:02d}",
            stato=STATI_FLOTTA[indice % len(STATI_FLOTTA)],
            km=(800 + indice * 140) if tipo == "ebike" else 9000 + indice * 1875,
        )
        for sede in sedi
        for indice, (tipo, targa) in enumerate(CONFIGURAZIONE_FLOTTA, start=1)
    ]
    db.add_all(veicoli)
    db.flush()
    clienti = [
        Cliente(
            tipo="azienda" if indice % 4 == 0 else "privato",
            nome=nome,
            email=f"cliente{indice}@demo.bubyrent.it",
        )
        for indice, nome in enumerate(NOMI_CLIENTI, start=1)
    ]
    db.add_all(clienti)
    db.flush()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    prenotazioni = [
        Prenotazione(
            veicolo_id=veicolo.id,
            cliente_id=clienti[indice % len(clienti)].id,
            inizio=adesso + timedelta(days=indice - 4),
            fine=adesso + timedelta(days=indice - 2),
            stato=("in_corso" if indice % 5 == 0 else "confermata"),
        )
        for indice, veicolo in enumerate(veicoli)
        if veicolo.stato in {"prenotato", "noleggiato"}
    ]
    db.add_all(prenotazioni)
    db.add_all(
        [
            Manutenzione(
                veicolo_id=veicolo.id,
                descrizione="Tagliando e controllo sicurezza",
                stato="in_corso",
                inizio=adesso - timedelta(days=indice + 2),
            )
            for indice, veicolo in enumerate(veicoli)
            if veicolo.stato == "in_manutenzione"
        ]
    )
    db.add_all(
        [
            Segnalazione(
                veicolo_id=veicolo.id,
                categoria="danno",
                testo="Danno rilevato durante la riconsegna",
                creato_il=adesso - timedelta(days=indice + 3),
            )
            for indice, veicolo in enumerate(veicoli)
            if veicolo.stato == "danneggiato"
        ]
    )
    db.commit()


def carica_dati_mock(db: Session) -> None:
    """Sedi e utenti demo; i dati mock si disattivano con SEED_DATI_MOCK=false."""
    if db.scalar(select(Sede.id).limit(1)) is None:
        sedi = [Sede(nome=nome, citta=citta) for nome, citta in SEDI_DEMO]
        db.add_all(sedi)
        db.flush()
        if settings.seed_dati_mock:
            _carica_flotta_demo(db, sedi)

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

    nuovi_operatori = []
    for sede_nome, email in OPERATORI_DEMO.items():
        sede = db.scalar(select(Sede).where(Sede.nome == sede_nome))
        if sede is not None and db.scalar(
            select(Utente.id).where(Utente.email_idx == blind_index(email))
        ) is None:
            nuovi_operatori.append(
                Utente(
                    email=email,
                    password_hash=hash_password(settings.operatore_password),
                    ruolo="operatore",
                    sede_id=sede.id,
                )
            )
    if nuovi_operatori:
        db.add_all(nuovi_operatori)
        db.commit()

    if db.scalar(
        select(Utente.id).where(Utente.email_idx == blind_index(settings.ceo_email))
    ) is None:
        db.add(
            Utente(
                email=settings.ceo_email,
                password_hash=hash_password(settings.ceo_password),
                ruolo="ceo",
            )
        )
        db.commit()
