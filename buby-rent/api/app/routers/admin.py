from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crypto import blind_index
from ..database import get_db
from ..deps import richiedi_ruoli
from ..models import Sede, Utente
from ..schemas import UtenteAdminAggiornaIn, UtenteAdminIn, UtenteOut
from ..security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/utenti", response_model=list[UtenteOut])
def lista_utenti(
    _: Utente = Depends(richiedi_ruoli("admin")),
    db: Session = Depends(get_db),
):
    return db.scalars(select(Utente).order_by(Utente.id)).all()


@router.post("/utenti", response_model=UtenteOut, status_code=201)
def crea_utente(
    dati: UtenteAdminIn,
    _: Utente = Depends(richiedi_ruoli("admin")),
    db: Session = Depends(get_db),
):
    email_norm = dati.email.strip().lower()
    esistente = db.scalar(select(Utente).where(Utente.email_idx == blind_index(email_norm)))
    if esistente is not None:
        raise HTTPException(409, "Email gia registrata")

    if dati.sede_id is not None and db.get(Sede, dati.sede_id) is None:
        raise HTTPException(404, "Sede non trovata")

    nuovo = Utente(
        email=email_norm,
        password_hash=hash_password(dati.password),
        ruolo=dati.ruolo,
        sede_id=dati.sede_id,
    )
    db.add(nuovo)
    db.commit()
    db.refresh(nuovo)
    return nuovo


@router.patch("/utenti/{utente_id}", response_model=UtenteOut)
def aggiorna_utente(
    utente_id: int,
    dati: UtenteAdminAggiornaIn,
    admin_corrente: Utente = Depends(richiedi_ruoli("admin")),
    db: Session = Depends(get_db),
):
    utente = db.get(Utente, utente_id)
    if utente is None:
        raise HTTPException(404, "Utente non trovato")

    nuovo_ruolo = dati.ruolo if dati.ruolo is not None else utente.ruolo
    if utente.id == admin_corrente.id and nuovo_ruolo != "admin":
        raise HTTPException(409, "Non puoi rimuovere il ruolo admin a te stesso")

    if dati.sede_id is not None and db.get(Sede, dati.sede_id) is None:
        raise HTTPException(404, "Sede non trovata")

    if nuovo_ruolo == "operatore":
        sede_finale = dati.sede_id if dati.sede_id is not None else utente.sede_id
        if sede_finale is None:
            raise HTTPException(422, "sede_id e obbligatoria per un operatore")
        utente.sede_id = sede_finale
    elif nuovo_ruolo in ("ceo", "admin", "cliente"):
        utente.sede_id = None

    utente.ruolo = nuovo_ruolo
    if dati.password is not None:
        utente.password_hash = hash_password(dati.password)

    db.commit()
    db.refresh(utente)
    return utente