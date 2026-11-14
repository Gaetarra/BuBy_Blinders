"""Accodamento delle email applicative.

L'API inserisce la coda nella stessa transazione dell'azione; il worker invia
solo dopo che la transazione è stata completata.
"""

from sqlalchemy.orm import Session

from .models import EmailDaInviare


def accoda_email(
    db: Session,
    *,
    destinatario: str,
    oggetto: str,
    corpo: str,
) -> EmailDaInviare:
    email = destinatario.strip().lower()
    if not email or email.endswith("@anonimo.invalid"):
        raise ValueError("destinatario email non valido")
    elemento = EmailDaInviare(
        destinatario=email,
        oggetto=oggetto,
        corpo=corpo,
    )
    db.add(elemento)
    return elemento
