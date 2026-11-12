from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import richiedi_ruoli, utente_corrente
from .models import (
    STATI_ATTIVI,
    STATI_PRENOTAZIONE,
    STATI_VEICOLO,
    Cliente,
    Ispezione,
    Manutenzione,
    Prenotazione,
    Segnalazione,
    Trasferimento,
    Utente,
    Veicolo,
)
from .schemas import (
    ClienteRiferimento,
    DashboardFlottaOut,
    IspezioneIn,
    IspezioneOut,
    ManutenzioneIn,
    ManutenzioneOut,
    PrenotazioneOut,
    SegnalazioneIn,
    SegnalazioneOut,
    TrasferimentoIn,
    TrasferimentoOut,
)

router = APIRouter(tags=["operazioni"])


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _controlla_sede(utente: Utente, veicolo: Veicolo):
    if utente.ruolo == "operatore" and utente.sede_id != veicolo.sede_id:
        raise HTTPException(403, "Puoi gestire solo i veicoli della tua sede")


@router.get("/clienti", response_model=list[ClienteRiferimento])
def elenco_clienti(
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    return [
        ClienteRiferimento(id=cliente_id)
        for cliente_id in db.scalars(
            select(Cliente.id).order_by(Cliente.id)
        )
    ]


@router.get("/dashboard/flotta", response_model=DashboardFlottaOut)
def dashboard_flotta(
    sede_id: int | None = None,
    stato_veicolo: str | None = None,
    stato_prenotazione: str | None = None,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    if utente.ruolo == "operatore":
        if utente.sede_id is None:
            raise HTTPException(403, "Operatore senza sede assegnata")
        if sede_id is not None and sede_id != utente.sede_id:
            raise HTTPException(403, "Puoi consultare solo la flotta della tua sede")
        sede_id = utente.sede_id
    elif sede_id is None:
        raise HTTPException(422, "sede_id obbligatorio per admin")

    if stato_veicolo is not None and stato_veicolo not in STATI_VEICOLO:
        raise HTTPException(422, "stato_veicolo non valido")
    if stato_prenotazione is not None and stato_prenotazione not in STATI_PRENOTAZIONE:
        raise HTTPException(422, "stato_prenotazione non valido")

    conteggi = dict(
        db.execute(
            select(Veicolo.stato, func.count(Veicolo.id))
            .where(Veicolo.sede_id == sede_id)
            .group_by(Veicolo.stato)
        ).all()
    )
    veicoli_query = select(Veicolo).where(Veicolo.sede_id == sede_id)
    if stato_veicolo:
        veicoli_query = veicoli_query.where(Veicolo.stato == stato_veicolo)

    prenotazioni_query = (
        select(Prenotazione)
        .join(Veicolo, Veicolo.id == Prenotazione.veicolo_id)
        .where(Veicolo.sede_id == sede_id, Prenotazione.stato.in_(STATI_ATTIVI))
    )
    if stato_prenotazione:
        prenotazioni_query = prenotazioni_query.where(
            Prenotazione.stato == stato_prenotazione
        )

    return DashboardFlottaOut(
        sede_id=sede_id,
        veicoli_totali=sum(conteggi.values()),
        veicoli_per_stato={stato: conteggi.get(stato, 0) for stato in STATI_VEICOLO},
        veicoli=list(db.scalars(veicoli_query.order_by(Veicolo.id))),
        prenotazioni=list(
            db.scalars(prenotazioni_query.order_by(Prenotazione.inizio))
        ),
    )


@router.get("/veicoli/{veicolo_id}/segnalazioni", response_model=list[SegnalazioneOut])
def lista_segnalazioni(
    veicolo_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    return list(
        db.query(Segnalazione)
        .filter(Segnalazione.veicolo_id == veicolo_id)
        .order_by(Segnalazione.creato_il.desc())
    )


@router.post("/veicoli/{veicolo_id}/segnalazioni", response_model=SegnalazioneOut, status_code=201)
def crea_segnalazione(
    veicolo_id: int,
    dati: SegnalazioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(utente_corrente),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    if utente.ruolo == "operatore":
        _controlla_sede(utente, veicolo)
    elif utente.ruolo == "cliente" and utente.cliente_id is None:
        raise HTTPException(403, "Solo i clienti possono aprire segnalazioni")

    segnalazione = Segnalazione(
        veicolo_id=veicolo_id,
        cliente_id=utente.cliente_id if utente.ruolo == "cliente" else None,
        categoria=dati.categoria.strip(),
        testo=dati.testo.strip(),
    )
    db.add(segnalazione)
    db.commit()
    db.refresh(segnalazione)
    return segnalazione


@router.get("/veicoli/{veicolo_id}/manutenzioni", response_model=list[ManutenzioneOut])
def lista_manutenzioni(
    veicolo_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    return list(
        db.query(Manutenzione)
        .filter(Manutenzione.veicolo_id == veicolo_id)
        .order_by(Manutenzione.inizio.desc().nullslast())
    )


@router.post("/veicoli/{veicolo_id}/manutenzioni", response_model=ManutenzioneOut, status_code=201)
def crea_manutenzione(
    veicolo_id: int,
    dati: ManutenzioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)

    manutenzione = Manutenzione(
        veicolo_id=veicolo_id,
        descrizione=dati.descrizione.strip(),
        stato=dati.stato,
        inizio=dati.inizio or _adesso(),
        fine=dati.fine,
    )
    if dati.stato in {"programmata", "in_corso"}:
        veicolo.stato = "in_manutenzione"
    db.add(manutenzione)
    db.commit()
    db.refresh(manutenzione)
    return manutenzione


@router.get("/veicoli/{veicolo_id}/trasferimenti", response_model=list[TrasferimentoOut])
def lista_trasferimenti(
    veicolo_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    return list(
        db.query(Trasferimento)
        .filter(Trasferimento.veicolo_id == veicolo_id)
        .order_by(Trasferimento.inizio.desc().nullslast())
    )


@router.post("/veicoli/{veicolo_id}/trasferimenti", response_model=TrasferimentoOut, status_code=201)
def crea_trasferimento(
    veicolo_id: int,
    dati: TrasferimentoIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    veicolo = db.get(Veicolo, veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    if veicolo.sede_id == dati.sede_destinazione_id:
        raise HTTPException(422, "La sede di destinazione deve essere diversa da quella di origine")

    trasferimento = Trasferimento(
        veicolo_id=veicolo_id,
        sede_origine_id=veicolo.sede_id,
        sede_destinazione_id=dati.sede_destinazione_id,
        inizio=dati.inizio or _adesso(),
        fine=dati.fine,
        stato=dati.stato,
        note=dati.note.strip() if dati.note else None,
    )
    veicolo.stato = "in_trasferimento"
    db.add(trasferimento)
    db.commit()
    db.refresh(trasferimento)
    return trasferimento


@router.patch("/trasferimenti/{trasferimento_id}/stato", response_model=TrasferimentoOut)
def aggiorna_trasferimento(
    trasferimento_id: int,
    stato: str = Query(..., description="Nuovo stato del trasferimento"),
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    trasferimento = db.get(Trasferimento, trasferimento_id)
    if trasferimento is None:
        raise HTTPException(404, "Trasferimento non trovato")
    veicolo = db.get(Veicolo, trasferimento.veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    if stato not in {"programmato", "in_corso", "completato", "annullato"}:
        raise HTTPException(422, "stato non valido")
    trasferimento.stato = stato
    if stato == "completato":
        veicolo.sede_id = trasferimento.sede_destinazione_id
        veicolo.stato = "disponibile"
        trasferimento.fine = trasferimento.fine or _adesso()
    elif stato == "annullato":
        veicolo.stato = "disponibile"
    db.commit()
    db.refresh(trasferimento)
    return trasferimento


@router.get("/prenotazioni/{prenotazione_id}/ispezioni", response_model=list[IspezioneOut])
def lista_ispezioni(
    prenotazione_id: int,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    prenotazione = db.get(Prenotazione, prenotazione_id)
    if prenotazione is None:
        raise HTTPException(404, "Prenotazione non trovata")
    veicolo = db.get(Veicolo, prenotazione.veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    return list(
        db.query(Ispezione)
        .filter(Ispezione.prenotazione_id == prenotazione_id)
        .order_by(Ispezione.creato_il.desc())
    )


@router.post("/prenotazioni/{prenotazione_id}/checkin", response_model=PrenotazioneOut)
def checkin_prenotazione(
    prenotazione_id: int,
    dati: IspezioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    prenotazione = db.get(Prenotazione, prenotazione_id)
    if prenotazione is None:
        raise HTTPException(404, "Prenotazione non trovata")
    veicolo = db.get(Veicolo, prenotazione.veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    if prenotazione.stato not in {"richiesta", "confermata"}:
        raise HTTPException(409, "La prenotazione non e in uno stato idoneo al check-in")
    if veicolo.stato in {"noleggiato", "in_manutenzione", "danneggiato", "in_trasferimento"}:
        raise HTTPException(409, "Il veicolo non e disponibile per il check-in")
    if any(
        ispezione.fase == "ritiro"
        for ispezione in db.scalars(
            select(Ispezione).where(Ispezione.prenotazione_id == prenotazione.id)
        )
    ):
        raise HTTPException(409, "Il check-in e gia stato registrato")
    if dati.km is not None and dati.km < veicolo.km:
        raise HTTPException(422, "I km del ritiro non possono essere inferiori a quelli registrati")

    prenotazione.stato = "in_corso"
    veicolo.stato = "noleggiato"
    if dati.km is not None:
        veicolo.km = dati.km
    db.add(
        Ispezione(
            prenotazione_id=prenotazione.id,
            fase="ritiro",
            km=dati.km,
            carburante=dati.carburante,
            batteria=dati.batteria,
            foto_url=dati.foto_url,
            note=dati.note,
        )
    )
    db.commit()
    db.refresh(prenotazione)
    return prenotazione


@router.post("/prenotazioni/{prenotazione_id}/checkout", response_model=PrenotazioneOut)
def checkout_prenotazione(
    prenotazione_id: int,
    dati: IspezioneIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    prenotazione = db.get(Prenotazione, prenotazione_id)
    if prenotazione is None:
        raise HTTPException(404, "Prenotazione non trovata")
    veicolo = db.get(Veicolo, prenotazione.veicolo_id)
    if veicolo is None:
        raise HTTPException(404, "Veicolo non trovato")
    _controlla_sede(utente, veicolo)
    if prenotazione.stato != "in_corso":
        raise HTTPException(409, "La prenotazione non e in corso")
    if dati.km is not None and dati.km < veicolo.km:
        raise HTTPException(422, "I km della riconsegna non possono diminuire")
    if db.scalar(
        select(Ispezione.id).where(
            Ispezione.prenotazione_id == prenotazione.id,
            Ispezione.fase == "riconsegna",
        )
    ):
        raise HTTPException(409, "Il check-out e gia stato registrato")

    prenotazione.stato = "conclusa"
    veicolo.stato = "danneggiato" if dati.danni_rilevati else "disponibile"
    if dati.km is not None:
        veicolo.km = dati.km
    db.add(
        Ispezione(
            prenotazione_id=prenotazione.id,
            fase="riconsegna",
            km=dati.km,
            carburante=dati.carburante,
            batteria=dati.batteria,
            foto_url=dati.foto_url,
            note=dati.note,
        )
    )
    if dati.danni_rilevati:
        db.add(
            Segnalazione(
                veicolo_id=veicolo.id,
                cliente_id=prenotazione.cliente_id,
                categoria="danno",
                testo=dati.note or "Danno rilevato al check-out",
            )
        )
    db.commit()
    db.refresh(prenotazione)
    return prenotazione
