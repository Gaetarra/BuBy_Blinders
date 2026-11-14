from app.models import EmailDaInviare
from .conftest import registra


def _crea(client, headers, **extra):
    r = client.post("/segnalazioni", json={"testo": "Spia accesa", **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_visibilita_per_ruolo(client, cliente, operatore, admin):
    altro = registra(client, "luca@example.com")
    s = _crea(client, cliente, veicolo_id=1)       # sede 1
    _crea(client, altro, veicolo_id=6)             # sede 2

    assert len(client.get("/segnalazioni", headers=cliente).json()) == 1
    assert client.get(f"/segnalazioni/{s['id']}", headers=altro).status_code == 404
    assert len(client.get("/segnalazioni", headers=operatore).json()) == 1   # solo la sua sede
    assert len(client.get("/segnalazioni", headers=admin).json()) == 2
    assert client.get("/segnalazioni").status_code == 401


def test_aggiornamento_assegnazione_e_note(client, cliente, operatore, admin):
    s = _crea(client, cliente, veicolo_id=1)
    url = f"/segnalazioni/{s['id']}"
    assert client.patch(url, json={"stato": "chiusa"}, headers=cliente).status_code == 403
    assert client.patch(url, json={"stato": "boh"}, headers=operatore).status_code == 422

    admin_id = client.get("/auth/me", headers=admin).json()["id"]
    r = client.patch(url, json={"stato": "in_lavorazione", "assegnata_a": admin_id}, headers=operatore)
    assert r.json()["stato"] == "in_lavorazione" and r.json()["assegnata_a"] == admin_id
    cliente_id = client.get("/auth/me", headers=cliente).json()["id"]
    assert client.patch(url, json={"assegnata_a": cliente_id}, headers=operatore).status_code == 422

    assert client.post(f"{url}/note", json={"testo": "Chiamare il cliente"}, headers=operatore).status_code == 201
    assert len(client.get(f"{url}/note", headers=operatore).json()) == 1
    assert client.get(f"{url}/note", headers=cliente).status_code == 403   # il cliente non vede le note


def test_cambio_stato_avvisa_il_cliente(client, cliente, operatore, db):
    s = _crea(client, cliente, veicolo_id=1)
    client.patch(f"/segnalazioni/{s['id']}", json={"categoria": "guasto"}, headers=operatore)
    assert db.query(EmailDaInviare).count() == 0          # nessun cambio di stato, nessuna email
    client.patch(f"/segnalazioni/{s['id']}", json={"stato": "chiusa"}, headers=operatore)
    email = db.query(EmailDaInviare).one()
    assert email.destinatario == "anna@example.com" and "SG-000001" in email.oggetto
