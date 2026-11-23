from datetime import datetime, timedelta
import os
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import parse_cors_origins
from app.main import app


def test_cors_origins_are_configurable_and_explicit():
    assert parse_cors_origins(None) == ["http://localhost:3000"]
    assert parse_cors_origins(" https://app.lovable.dev/, http://localhost:3000 ") == [
        "https://app.lovable.dev",
        "http://localhost:3000",
    ]

    try:
        parse_cors_origins("*")
    except ValueError as error:
        assert "origini esplicite" in str(error)
    else:
        raise AssertionError("Wildcard CORS must be rejected")


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _periodo():
    inizio = datetime.now().replace(microsecond=0) + timedelta(days=3)
    return inizio.isoformat(), (inizio + timedelta(days=1)).isoformat()


def test_health_and_request_logging(client: TestClient, caplog):
    response = client.get("/health?private_query=do-not-log")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id
    assert "method=GET path=/health status_code=200" in caplog.text
    assert f"request_id={request_id}" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "private_query" not in caplog.text
    log_file = Path(os.environ["API_LOG_FILE"])
    assert log_file.exists()
    assert f"request_id={request_id}" in log_file.read_text()


def test_login_redacts_credentials_and_rejects_bad_password(
    client: TestClient, caplog
):
    response = client.post(
        "/auth/login",
        data={"username": "admin@example.test", "password": "admin-test-password"},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token not in caplog.text
    assert "admin-test-password" not in caplog.text

    failure = client.post(
        "/auth/login",
        data={"username": "admin@example.test", "password": "wrong-password"},
    )
    assert failure.status_code == 401
    assert "status_code=401" in caplog.text
    assert "wrong-password" not in caplog.text


def test_unhandled_error_is_logged_without_exception_message(
    client: TestClient, caplog
):
    def fail():
        raise RuntimeError("sensitive exception message")

    route = APIRoute(
        path="/_test/log-failure",
        endpoint=fail,
        methods=["GET"],
        include_in_schema=False,
    )
    app.router.routes.append(route)
    try:
        response = client.get("/_test/log-failure")
    finally:
        app.router.routes.remove(route)

    assert response.status_code == 500
    assert "path=/_test/log-failure status_code=500" in caplog.text
    assert "error_type=RuntimeError" in caplog.text
    assert "sensitive exception message" not in caplog.text
    log_file = Path(os.environ["API_LOG_FILE"])
    assert "error_type=RuntimeError" in log_file.read_text()
    assert "sensitive exception message" not in log_file.read_text()


def test_supabase_jwt_links_existing_user_and_database_role_is_authoritative(
    client: TestClient, monkeypatch, supabase_identity
):
    _, create_token = supabase_identity
    supabase_id, token = create_token(app_metadata={"role": "admin"})
    monkeypatch.setattr(
        "app.routers.auth.recupera_utente_supabase",
        lambda _token: {
            "id": supabase_id,
            "email": "operatore@example.test",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
        },
    )
    headers = {"Authorization": f"Bearer {token}"}

    provision = client.post("/auth/supabase/provision", headers=headers, json={})
    assert provision.status_code == 200
    assert provision.json()["ruolo"] == "operatore"

    profile = client.get("/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["ruolo"] == "operatore"

    dashboard = client.get("/dashboard/flotta", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["sede_id"] == 1


def test_supabase_customer_provision_requires_privacy_acceptance(
    client: TestClient, monkeypatch, supabase_identity
):
    _, create_token = supabase_identity
    supabase_id, token = create_token()
    monkeypatch.setattr(
        "app.routers.auth.recupera_utente_supabase",
        lambda _token: {
            "id": supabase_id,
            "email": "nuovo@example.test",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
        },
    )
    headers = {"Authorization": f"Bearer {token}"}

    missing_consent = client.post(
        "/auth/supabase/provision",
        headers=headers,
        json={"nome": "Nuovo Cliente"},
    )
    assert missing_consent.status_code == 422

    provision = client.post(
        "/auth/supabase/provision",
        headers=headers,
        json={
            "nome": "Nuovo Cliente",
            "accetta_privacy": True,
        },
    )
    assert provision.status_code == 200
    assert provision.json()["ruolo"] == "cliente"
    assert provision.json()["cliente_id"] is not None

    profile = client.get("/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == provision.json()["id"]


def test_supabase_customer_deletion_removes_identity_link(
    client: TestClient, monkeypatch, supabase_identity
):
    _, create_token = supabase_identity
    supabase_id, token = create_token()
    monkeypatch.setattr(
        "app.routers.auth.recupera_utente_supabase",
        lambda _token: {
            "id": supabase_id,
            "email": "eliminabile@example.test",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
        },
    )
    headers = {"Authorization": f"Bearer {token}"}

    provision = client.post(
        "/auth/supabase/provision",
        headers=headers,
        json={"nome": "Cliente da eliminare", "accetta_privacy": True},
    )
    assert provision.status_code == 200

    deletion = client.delete("/auth/me", headers=headers)
    assert deletion.status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 403


def test_supabase_rejects_invalid_signature_and_disables_local_login(
    client: TestClient, supabase_identity
):
    _, create_token = supabase_identity
    _, token = create_token()
    header, payload, signature = token.split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    invalid_token = f"{header}.{payload}.{signature}"

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401

    legacy_login = client.post(
        "/auth/login",
        data={"username": "admin@example.test", "password": "admin-test-password"},
    )
    assert legacy_login.status_code == 410


def test_customer_booking_is_self_and_operator_must_select_customer(
    client: TestClient,
):
    inizio, fine = _periodo()
    customer_token = login(
        client, "cliente@example.test", "customer-test-password"
    )
    customer_booking = client.post(
        "/prenotazioni",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"veicolo_id": 1, "inizio": inizio, "fine": fine, "cliente_id": 2},
    )
    assert customer_booking.status_code == 201
    assert customer_booking.json()["cliente_id"] == 1

    operator_token = login(
        client, "operatore@example.test", "operator-test-password"
    )
    no_customer = client.post(
        "/prenotazioni",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"veicolo_id": 2, "inizio": inizio, "fine": fine},
    )
    assert no_customer.status_code == 422
    assert no_customer.json()["detail"] == "cliente_id obbligatorio per operatori e admin"

    client_ids = client.get(
        "/clienti", headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert client_ids.status_code == 200
    assert client_ids.json() == [{"id": 1}, {"id": 2}]

    operator_booking = client.post(
        "/prenotazioni",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "veicolo_id": 2,
            "cliente_id": 2,
            "inizio": inizio,
            "fine": fine,
        },
    )
    assert operator_booking.status_code == 201
    assert operator_booking.json()["cliente_id"] == 2


def test_booking_overlap_returns_conflict(client: TestClient):
    token = login(client, "admin@example.test", "admin-test-password")
    inizio, fine = _periodo()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "veicolo_id": 1,
        "cliente_id": 1,
        "inizio": inizio,
        "fine": fine,
    }

    assert client.post("/prenotazioni", headers=headers, json=payload).status_code == 201
    conflict = client.post("/prenotazioni", headers=headers, json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "Veicolo gia prenotato nel periodo richiesto"


def test_customer_cannot_access_dashboard_and_operator_is_sede_scoped(
    client: TestClient,
):
    customer_token = login(
        client, "cliente@example.test", "customer-test-password"
    )
    denied = client.get(
        "/dashboard/flotta?sede_id=1",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert denied.status_code == 403

    operator_token = login(
        client, "operatore@example.test", "operator-test-password"
    )
    dashboard = client.get(
        "/dashboard/flotta",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["sede_id"] == 1
    assert dashboard.json()["veicoli_totali"] == 2

    other_branch = client.get(
        "/dashboard/flotta?sede_id=2",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert other_branch.status_code == 403


def test_sedi_endpoint_returns_only_own_sede_to_operator(client: TestClient):
    operator_token = login(
        client, "operatore@example.test", "operator-test-password"
    )
    sedi_operatore = client.get(
        "/dashboard/sedi",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert sedi_operatore.status_code == 200
    assert [sede["id"] for sede in sedi_operatore.json()] == [1]

    ceo_token = login(client, "ceo@example.test", "ceo-test-password")
    sedi_ceo = client.get(
        "/dashboard/sedi",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert sedi_ceo.status_code == 200
    assert [sede["id"] for sede in sedi_ceo.json()] == [1, 2]

    customer_token = login(
        client, "cliente@example.test", "customer-test-password"
    )
    negato = client.get(
        "/dashboard/sedi",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert negato.status_code == 403


def test_checkin_checkout_updates_vehicle_and_records_damage(client: TestClient):
    token = login(client, "admin@example.test", "admin-test-password")
    headers = {"Authorization": f"Bearer {token}"}
    inizio, fine = _periodo()
    booking = client.post(
        "/prenotazioni",
        headers=headers,
        json={
            "veicolo_id": 1,
            "cliente_id": 1,
            "inizio": inizio,
            "fine": fine,
        },
    )
    assert booking.status_code == 201
    booking_id = booking.json()["id"]

    checkin = client.post(
        f"/prenotazioni/{booking_id}/checkin",
        headers=headers,
        json={"km": 101, "carburante": 80, "foto_url": "https://example.test/ritiro.jpg"},
    )
    assert checkin.status_code == 200
    assert checkin.json()["stato"] == "in_corso"

    duplicate_checkin = client.post(
        f"/prenotazioni/{booking_id}/checkin",
        headers=headers,
        json={"km": 101},
    )
    assert duplicate_checkin.status_code == 409

    checkout = client.post(
        f"/prenotazioni/{booking_id}/checkout",
        headers=headers,
        json={
            "km": 110,
            "carburante": 60,
            "danni_rilevati": True,
            "note": "Danno al paraurti",
        },
    )
    assert checkout.status_code == 200
    assert checkout.json()["stato"] == "conclusa"

    inspections = client.get(
        f"/prenotazioni/{booking_id}/ispezioni", headers=headers
    )
    assert inspections.status_code == 200
    assert {inspection["fase"] for inspection in inspections.json()} == {
        "ritiro",
        "riconsegna",
    }

    reports = client.get("/veicoli/1/segnalazioni", headers=headers)
    assert reports.status_code == 200
    assert reports.json()[0]["categoria"] == "danno"
    assert reports.json()[0]["cliente_id"] == 1

    vehicle = client.get("/veicoli/disponibili", params={
        "sede_id": 1,
        "da": inizio,
        "a": fine,
    })
    assert vehicle.status_code == 200
    assert all(item["id"] != 1 for item in vehicle.json())


def test_internal_communications_roles_and_sede_scope(client: TestClient):
    operator_token = login(
        client, "operatore@example.test", "operator-test-password"
    )
    operator_headers = {"Authorization": f"Bearer {operator_token}"}

    created = client.post(
        "/dashboard/comunicazioni",
        headers=operator_headers,
        json={"testo": "Nota operatore", "veicolo_id": 1},
    )
    assert created.status_code == 201
    assert created.json()["sede_id"] == 1

    denied = client.post(
        "/dashboard/comunicazioni",
        headers=operator_headers,
        json={"testo": "Veicolo di un'altra sede", "veicolo_id": 3},
    )
    assert denied.status_code == 403

    admin_token = login(client, "admin@example.test", "admin-test-password")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    other = client.post(
        "/dashboard/comunicazioni",
        headers=admin_headers,
        json={"testo": "Nota altra sede", "veicolo_id": 3},
    )
    assert other.status_code == 201

    unassigned = client.post(
        "/dashboard/comunicazioni",
        headers=admin_headers,
        json={"testo": "Nota non smistata"},
    )
    assert unassigned.status_code == 201
    assert unassigned.json()["sede_id"] is None

    operator_listing = client.get(
        "/dashboard/comunicazioni", headers=operator_headers
    )
    assert operator_listing.status_code == 200
    testi = {item["testo"] for item in operator_listing.json()}
    assert "Nota operatore" in testi
    assert "Nota non smistata" in testi
    assert "Nota altra sede" not in testi

    denied_patch = client.patch(
        f"/dashboard/comunicazioni/{other.json()['id']}/assegnazione",
        headers=operator_headers,
        params={"assegnato_a_id": 2},
    )
    assert denied_patch.status_code == 403

    taken = client.patch(
        f"/dashboard/comunicazioni/{created.json()['id']}/assegnazione",
        headers=operator_headers,
        params={"assegnato_a_id": 2},
    )
    assert taken.status_code == 200
    assert taken.json()["assegnato_a_id"] == 2

    ceo_token = login(client, "ceo@example.test", "ceo-test-password")
    ceo_headers = {"Authorization": f"Bearer {ceo_token}"}
    assert (
        client.get("/dashboard/comunicazioni", headers=ceo_headers).status_code == 200
    )
    assert (
        client.post(
            "/dashboard/comunicazioni",
            headers=ceo_headers,
            json={"testo": "Nota del CEO"},
        ).status_code
        == 403
    )
