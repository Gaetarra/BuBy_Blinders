import os
import tempfile
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault(
    "API_LOG_FILE", str(Path(tempfile.gettempdir()) / "buby-rent-test-api.log")
)

import jwt
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Cliente, Sede, Utente, Veicolo
from app.security import hash_password
from app.config import settings
from app import supabase_auth


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with test_sessions() as db:
            yield db

    @asynccontextmanager
    async def no_app_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = no_app_lifespan
    app.dependency_overrides[get_db] = override_get_db

    with test_sessions() as db:
        db.add_all(
            [
                Sede(id=1, nome="Torino Centro", citta="Torino"),
                Sede(id=2, nome="Lago Maggiore", citta="Stresa"),
            ]
        )
        db.flush()
        db.add_all(
            [
                Veicolo(id=1, sede_id=1, tipo="auto", targa="TEST001", km=100),
                Veicolo(id=2, sede_id=1, tipo="furgone", targa="TEST002", km=200),
                Veicolo(id=3, sede_id=2, tipo="ebike", targa="TEST003", km=0),
                Cliente(id=1, tipo="privato", nome="Cliente Uno", email="uno@example.test"),
                Cliente(id=2, tipo="azienda", nome="Cliente Due", email="due@example.test"),
            ]
        )
        db.flush()
        db.add_all(
            [
                Utente(
                    email="admin@example.test",
                    password_hash=hash_password("admin-test-password"),
                    ruolo="admin",
                ),
                Utente(
                    email="operatore@example.test",
                    password_hash=hash_password("operator-test-password"),
                    ruolo="operatore",
                    sede_id=1,
                ),
                Utente(
                    email="cliente@example.test",
                    password_hash=hash_password("customer-test-password"),
                    ruolo="cliente",
                    cliente_id=1,
                ),
            ]
        )
        db.commit()

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan
        Base.metadata.drop_all(engine)
        engine.dispose()


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def supabase_identity(monkeypatch):
    project_url = "https://buby-test.supabase.co"
    publishable_key = "sb_publishable_test_key"
    monkeypatch.setattr(settings, "supabase_url", project_url)
    monkeypatch.setattr(settings, "supabase_publishable_key", publishable_key)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(supabase_auth, "_jwk_client", lambda _url: FakeJwkClient())

    def create_token(user_id=None, **claims):
        user_id = user_id or str(uuid4())
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "iss": f"{project_url}/auth/v1",
            "role": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=10),
            **claims,
        }
        return user_id, jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return project_url, create_token
