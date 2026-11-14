import os
import tempfile

# database di prova isolato: va impostato PRIMA di importare l'app
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # all'avvio crea le tabelle e carica i dati mock
        yield c


@pytest.fixture
def db(client):
    with SessionLocal() as sessione:
        yield sessione


def token(client, email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return token(client, settings.admin_email, settings.admin_password)


@pytest.fixture
def operatore(client):  # operatore della sede 1 (Torino Centro)
    return token(client, "operatore@buby.it", settings.operatore_password)


def registra(client, email, nome="Utente Prova"):
    r = client.post(
        "/auth/register",
        json={"nome": nome, "email": email, "password": "password123", "accetta_privacy": True},
    )
    assert r.status_code == 201, r.text
    return token(client, email, "password123")


@pytest.fixture
def cliente(client):
    return registra(client, "anna@example.com", "Anna Bianchi")
