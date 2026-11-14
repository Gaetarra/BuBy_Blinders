from sqlalchemy import text

from app.database import engine
from app.models import EmailDaInviare
from .conftest import registra, token


def test_dati_personali_cifrati_nel_database(client, cliente):
    client.post("/segnalazioni", json={"oggetto": "Graffio", "testo": "Graffio sul paraurti"}, headers=cliente)
    with engine.connect() as conn:
        contenuto = " ".join(
            str(v)
            for tabella, colonne in (
                ("clienti", "nome, email"),
                ("utenti", "email"),
                ("segnalazioni", "mittente_email, oggetto, testo"),
            )
            for riga in conn.execute(text(f"select {colonne} from {tabella}"))
            for v in riga
        )
    for in_chiaro in ("Anna", "example.com", "Graffio"):
        assert in_chiaro not in contenuto


def test_login_con_email_di_case_diverso(client, cliente):
    r = client.post("/auth/login", data={"username": "ANNA@Example.com", "password": "password123"})
    assert r.status_code == 200


def test_registrazione_senza_privacy_rifiutata(client):
    r = client.post("/auth/register", json={"nome": "A", "email": "a@example.com", "password": "password123", "accetta_privacy": False})
    assert r.status_code == 422


def test_export_e_cancellazione(client, cliente, operatore, db):
    s = client.post("/segnalazioni", json={"veicolo_id": 1, "testo": "Dati miei"}, headers=cliente).json()
    client.post(f"/segnalazioni/{s['id']}/note", json={"testo": "nota"}, headers=operatore)
    passata = {"veicolo_id": 2, "inizio": "2025-01-10T09:00:00", "fine": "2025-01-12T09:00:00"}
    client.post("/prenotazioni", json=passata, headers=cliente)

    export = client.get("/auth/me/dati", headers=cliente).json()
    assert len(export["prenotazioni"]) == 1 and len(export["segnalazioni"]) == 1

    assert client.delete("/auth/me", headers=cliente).status_code == 204
    assert client.get("/auth/me", headers=cliente).status_code == 401

    db.expire_all()
    from app.models import Cliente, NotaInterna, Segnalazione

    assert db.get(Cliente, 2).nome == "Utente eliminato"
    seg = db.get(Segnalazione, s["id"])
    assert seg.mittente_email is None and "rimosso" in seg.testo
    assert db.query(NotaInterna).one().testo == "[rimosso]"
    assert all(e.destinatario.endswith("anonimo.invalid") for e in db.query(EmailDaInviare))
    registra(client, "anna@example.com")  # l'email si puo registrare di nuovo


def test_cancellazione_bloccata_con_prenotazioni_attive(client, cliente):
    futura = {"veicolo_id": 1, "inizio": "2030-01-10T09:00:00", "fine": "2030-01-12T09:00:00"}
    client.post("/prenotazioni", json=futura, headers=cliente)
    assert client.delete("/auth/me", headers=cliente).status_code == 409


def test_collegamento_con_anagrafica_importata(client, db):
    from app.config import settings
    from app.models import Cliente

    db.add(Cliente(nome="Giulia Neri", email="giulia@example.com"))
    db.commit()
    body = {"nome": "X", "email": "giulia@example.com", "password": "password123", "accetta_privacy": True}
    assert client.post("/auth/register", json=body).status_code == 201

    db.add(Cliente(nome="Paolo", email="paolo@example.com"))
    db.commit()
    settings.collega_clienti_importati = False
    try:
        assert client.post("/auth/register", json={**body, "email": "paolo@example.com"}).status_code == 409
    finally:
        settings.collega_clienti_importati = True
