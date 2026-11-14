PERIODO = {"inizio": "2030-01-10T09:00:00", "fine": "2030-01-12T09:00:00"}


def test_ricerca_pubblica_e_doppia_prenotazione(client, cliente):
    p = {"sede_id": 1, "da": PERIODO["inizio"], "a": PERIODO["fine"], "tipo": "auto"}
    assert len(client.get("/veicoli/disponibili", params=p).json()) == 2

    assert client.post("/prenotazioni", json={"veicolo_id": 1, **PERIODO}, headers=cliente).status_code == 201
    assert client.post("/prenotazioni", json={"veicolo_id": 1, **PERIODO}, headers=cliente).status_code == 409
    assert len(client.get("/veicoli/disponibili", params=p).json()) == 1


def test_prenotare_richiede_login_e_date_valide(client, cliente):
    assert client.post("/prenotazioni", json={"veicolo_id": 1, **PERIODO}).status_code == 401
    storte = {"veicolo_id": 1, "inizio": PERIODO["fine"], "fine": PERIODO["inizio"]}
    assert client.post("/prenotazioni", json=storte, headers=cliente).status_code == 422


def test_ruoli_su_stato_veicolo(client, cliente, operatore):
    assert client.patch("/veicoli/1/stato", json={"stato": "danneggiato"}, headers=cliente).status_code == 403
    assert client.patch("/veicoli/1/stato", json={"stato": "danneggiato"}, headers=operatore).status_code == 200
    assert client.patch("/veicoli/6/stato", json={"stato": "danneggiato"}, headers=operatore).status_code == 403  # altra sede


def test_conferma_prenotazione_in_coda(client, cliente, db):
    from app.models import EmailDaInviare

    client.post("/prenotazioni", json={"veicolo_id": 1, **PERIODO}, headers=cliente)
    email = db.query(EmailDaInviare).one()
    assert email.destinatario == "anna@example.com"
    assert "BR-000001" in email.oggetto and email.stato == "da_inviare"
