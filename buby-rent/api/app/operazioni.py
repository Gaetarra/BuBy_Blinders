from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, true
from sqlalchemy.orm import Session

from .database import get_db
from .deps import richiedi_ruoli, utente_corrente
from .models import (
    STATI_ATTIVI,
    STATI_PRENOTAZIONE,
    STATI_VEICOLO,
    Cliente,
    ComunicazioneInterna,
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
    ComunicazioneInternaIn,
    ComunicazioneInternaOut,
    DashboardFlottaOut,
    FermoOut,
    IspezioneIn,
    IspezioneOut,
    ManutenzioneIn,
    ManutenzioneOut,
    PrenotazioneOut,
    SegnalazioneIn,
    SegnalazioneOut,
    TrasferimentoIn,
    TrasferimentoOut,
    OperatoreOut,
)

router = APIRouter(tags=["operazioni"])


def _adesso() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _controlla_sede(utente: Utente, veicolo: Veicolo):
    if utente.ruolo == "operatore" and utente.sede_id != veicolo.sede_id:
        raise HTTPException(403, "Puoi gestire solo i veicoli della tua sede")


@router.get("/dashboard/operatori", response_model=list[OperatoreOut])
def elenco_operatori(
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("admin", "ceo")),
):
    return list(
        db.scalars(select(Utente).where(Utente.ruolo == "operatore").order_by(Utente.id))
    )


@router.get("/dashboard/comunicazioni", response_model=list[ComunicazioneInternaOut])
def dashboard_comunicazioni(
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
):
    query = select(ComunicazioneInterna).order_by(ComunicazioneInterna.creato_il.desc())
    if utente.ruolo == "operatore":
        if utente.sede_id is None:
            raise HTTPException(403, "Operatore senza sede assegnata")
        query = query.where(
            or_(
                ComunicazioneInterna.sede_id == utente.sede_id,
                ComunicazioneInterna.sede_id.is_(None),
            )
        )
    return list(db.scalars(query))


@router.post(
    "/dashboard/comunicazioni",
    response_model=ComunicazioneInternaOut,
    status_code=201,
)
def crea_comunicazione(
    dati: ComunicazioneInternaIn,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    sede_id = dati.sede_id
    if dati.veicolo_id is not None:
        veicolo = db.get(Veicolo, dati.veicolo_id)
        if veicolo is None:
            raise HTTPException(404, "Veicolo non trovato")
        if utente.ruolo == "operatore" and veicolo.sede_id != utente.sede_id:
            raise HTTPException(403, "Puoi usare solo veicoli della tua sede")
        if sede_id is not None and sede_id != veicolo.sede_id:
            raise HTTPException(422, "La sede non corrisponde al veicolo")
        sede_id = veicolo.sede_id
    if utente.ruolo == "operatore":
        if utente.sede_id is None:
            raise HTTPException(403, "Operatore senza sede assegnata")
        if sede_id is not None and sede_id != utente.sede_id:
            raise HTTPException(403, "Puoi creare comunicazioni solo per la tua sede")
        sede_id = utente.sede_id
        if dati.assegnato_a_id not in (None, utente.id):
            raise HTTPException(403, "Puoi assegnare la comunicazione solo a te stesso")
    assegnato = None
    if dati.assegnato_a_id is not None:
        assegnato = db.get(Utente, dati.assegnato_a_id)
        if assegnato is None or assegnato.ruolo != "operatore":
            raise HTTPException(422, "L'assegnatario deve essere un operatore")
        if sede_id is not None and assegnato.sede_id != sede_id:
            raise HTTPException(422, "L'assegnatario non appartiene alla sede")
    comunicazione = ComunicazioneInterna(
        sede_id=sede_id,
        veicolo_id=dati.veicolo_id,
        testo=dati.testo.strip(),
        creato_da_id=utente.id,
        assegnato_a_id=dati.assegnato_a_id,
    )
    db.add(comunicazione)
    db.commit()
    db.refresh(comunicazione)
    return comunicazione


@router.patch(
    "/dashboard/comunicazioni/{comunicazione_id}/assegnazione",
    response_model=ComunicazioneInternaOut,
)
def assegna_comunicazione(
    comunicazione_id: int,
    assegnato_a_id: int | None = None,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin")),
):
    comunicazione = db.get(ComunicazioneInterna, comunicazione_id)
    if comunicazione is None:
        raise HTTPException(404, "Comunicazione non trovata")
    if utente.ruolo == "operatore" and comunicazione.sede_id not in (None, utente.sede_id):
        raise HTTPException(403, "Puoi gestire solo le comunicazioni della tua sede")
    if assegnato_a_id is not None:
        assegnato = db.get(Utente, assegnato_a_id)
        if assegnato is None or assegnato.ruolo != "operatore":
            raise HTTPException(422, "L'assegnatario deve essere un operatore")
        if comunicazione.sede_id is not None and assegnato.sede_id != comunicazione.sede_id:
            raise HTTPException(422, "L'assegnatario non appartiene alla sede")
    comunicazione.assegnato_a_id = assegnato_a_id
    comunicazione.stato = "presa_in_carico" if assegnato_a_id is not None else "aperta"
    db.commit()
    db.refresh(comunicazione)
    return comunicazione


@router.get("/dashboard/fermi", response_model=list[FermoOut])
def dashboard_fermi(
    sede_id: int | None = None,
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
):
    if utente.ruolo == "operatore":
        if utente.sede_id is None:
            raise HTTPException(403, "Operatore senza sede assegnata")
        if sede_id is not None and sede_id != utente.sede_id:
            raise HTTPException(403, "Puoi consultare solo i mezzi della tua sede")
        sede_id = utente.sede_id
    elif utente.ruolo == "admin" and sede_id is None:
        raise HTTPException(422, "sede_id obbligatorio per admin")

    veicoli = list(
        db.scalars(
            select(Veicolo)
            .where(
                true() if sede_id is None else Veicolo.sede_id == sede_id,
                Veicolo.stato.in_(("in_manutenzione", "danneggiato")),
            )
            .order_by(Veicolo.id)
        )
    )
    fermi = []
    adesso = _adesso()
    for veicolo in veicoli:
        manutenzione = db.scalar(
            select(Manutenzione)
            .where(Manutenzione.veicolo_id == veicolo.id)
            .order_by(Manutenzione.inizio.desc().nullslast())
        )
        segnalazione = db.scalar(
            select(Segnalazione)
            .where(Segnalazione.veicolo_id == veicolo.id)
            .order_by(Segnalazione.creato_il.desc())
        )
        date_fermo = [
            data
            for data in (
                manutenzione.inizio if manutenzione else None,
                segnalazione.creato_il if segnalazione else None,
            )
            if data is not None
        ]
        ultimo_aggiornamento = max(date_fermo, default=adesso)
        giorni_fermo = max(0, (adesso - ultimo_aggiornamento).days)
        priorita = (100 if veicolo.stato == "danneggiato" else 50) + min(
            giorni_fermo, 30
        )
        fermi.append(
            FermoOut(
                veicolo=veicolo,
                priorita=priorita,
                giorni_fermo=giorni_fermo,
                motivo=(
                    "Danno segnalato"
                    if veicolo.stato == "danneggiato"
                    else "Manutenzione necessaria"
                ),
            )
        )
    return sorted(fermi, key=lambda fermo: (-fermo.priorita, -fermo.giorni_fermo))


@router.get("/clienti", response_model=list[ClienteRiferimento])
def elenco_clienti(
    db: Session = Depends(get_db),
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
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
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
):
    if utente.ruolo == "operatore":
        if utente.sede_id is None:
            raise HTTPException(403, "Operatore senza sede assegnata")
        if sede_id is not None and sede_id != utente.sede_id:
            raise HTTPException(403, "Puoi consultare solo la flotta della tua sede")
        sede_id = utente.sede_id
    elif utente.ruolo == "admin" and sede_id is None:
        raise HTTPException(422, "sede_id obbligatorio per admin")

    if stato_veicolo is not None and stato_veicolo not in STATI_VEICOLO:
        raise HTTPException(422, "stato_veicolo non valido")
    if stato_prenotazione is not None and stato_prenotazione not in STATI_PRENOTAZIONE:
        raise HTTPException(422, "stato_prenotazione non valido")

    conteggi = dict(
        db.execute(
            select(Veicolo.stato, func.count(Veicolo.id))
            .where(true() if sede_id is None else Veicolo.sede_id == sede_id)
            .group_by(Veicolo.stato)
        ).all()
    )
    veicoli_query = select(Veicolo).where(
        true() if sede_id is None else Veicolo.sede_id == sede_id
    )
    if stato_veicolo:
        veicoli_query = veicoli_query.where(Veicolo.stato == stato_veicolo)

    prenotazioni_query = (
        select(Prenotazione)
        .join(Veicolo, Veicolo.id == Prenotazione.veicolo_id)
        .where(
            true() if sede_id is None else Veicolo.sede_id == sede_id,
            Prenotazione.stato.in_(STATI_ATTIVI),
        )
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
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
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
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
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
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
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
    utente: Utente = Depends(richiedi_ruoli("operatore", "admin", "ceo")),
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
