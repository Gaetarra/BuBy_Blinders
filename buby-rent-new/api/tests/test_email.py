from datetime import datetime

from app import casella, email_uscita
from app.messaggi import ricevi_messaggio
from app.models import Cliente, EmailDaInviare, Prenotazione, Segnalazione
from .conftest import registra

ORA = datetime(2026, 11, 14, 10, 0)


def _ricevi(db, **kw):
    base = dict(mittente="anna@example.com", destinatario="assistenza@buby.it", oggetto="Aiuto", testo="Testo", data=ORA, message_id="m1@x")
    risultato = ricevi_messaggio(db, **{**base, **kw})
    db.commit()
    return risultato


def test_messaggio_da_cliente_con_codice_prenotazione(client, cliente, db):
    client.post("/prenotazioni", json={"veicolo_id": 6, "inizio": "2030-01-10T09:00:00", "fine": "2030-01-11T09:00:00"}, headers=cliente)
    s = _ricevi(db, oggetto="Re: Prenotazione BR-000001 confermata")
    assert s.prenotazione_id == 1 and s.veicolo_id == 6 and s.sede_id == 2 and s.canale == "email"
    assert s.cliente_id == db.query(Cliente).filter(Cliente.id == s.cliente_id).one().id


def test_codice_di_prenotazione_altrui_non_collega(client, cliente, db):
    client.post("/prenotazioni", json={"veicolo_id": 6, "inizio": "2030-01-10T09:00:00", "fine": "2030-01-11T09:00:00"}, headers=cliente)
    s = _ricevi(db, mittente="sconosciuto@example.com", oggetto="BR-000001", message_id="m2@x")
    assert s.prenotazione_id is None and s.veicolo_id is None and s.cliente_id is None


def test_smistamento_per_sede_scarti_e_duplicati(client, db):
    assert _ricevi(db, destinatario="assistenza.stresa@buby.it").sede_id == 2
    assert _ricevi(db, destinatario="assistenza.torino@buby.it", message_id="m3@x").sede_id == 1
    assert _ricevi(db, message_id="m4@x").sede_id is None
    assert _ricevi(db, message_id="m4@x") is None                     # duplicato
    assert _ricevi(db, mittente="non-una-email", message_id="m5@x") is None
    assert _ricevi(db, testo="   ", message_id="m6@x") is None
    assert db.query(Segnalazione).count() == 3


def test_invio_coda_e_gestione_errori(client, cliente, db, monkeypatch):
    client.post("/prenotazioni", json={"veicolo_id": 1, "inizio": "2030-01-10T09:00:00", "fine": "2030-01-11T09:00:00"}, headers=cliente)
    inviate = []
    monkeypatch.setattr(email_uscita, "_smtp_invia", lambda d, o, c: inviate.append((d, o)))
    assert email_uscita.invia_coda(db) == (1, 0)
    email = db.query(EmailDaInviare).one()
    assert email.stato == "inviata" and email.corpo == email_uscita.CORPO_RIMOSSO
    assert inviate == [("anna@example.com", "Prenotazione BR-000001 confermata")]

    email_uscita.accoda_email(db, "x@example.com", "Prova", "corpo")
    db.commit()

    def guasto(*a):
        raise ConnectionRefusedError("mail.example.com rifiuta la connessione")

    monkeypatch.setattr(email_uscita, "_smtp_invia", guasto)
    for _ in range(email_uscita.MAX_TENTATIVI):
        email_uscita.invia_coda(db)
    nuova = db.query(EmailDaInviare).order_by(EmailDaInviare.id.desc()).first()
    assert nuova.stato == "errore" and nuova.errore == "ConnectionRefusedError"  # niente indirizzi nell'errore


def test_non_si_accodano_email_a_indirizzi_anonimizzati(db):
    assert email_uscita.accoda_email(db, "eliminato-3@anonimo.invalid", "x", "y") is None
    assert email_uscita.accoda_email(db, None, "x", "y") is None


def test_lettura_casella(client, db, monkeypatch):
    registra(client, "anna@example.com")
    risposte = {
        "/api/v1/messages?limit=100": {"messages": [
            {"ID": "A", "MessageID": "a@x", "From": {"Address": "anna@example.com"}, "To": [{"Address": "assistenza.torino@buby.it"}], "Subject": "Freno", "Created": "2026-11-14T10:00:00Z"},
            {"ID": "B", "MessageID": "b@x", "From": {"Address": "noreply@buby.it"}, "To": [{"Address": "anna@example.com"}], "Subject": "Conferma", "Created": "2026-11-14T10:01:00Z"},
            {"ID": "C", "MessageID": "c@x", "From": {"Address": "robot@example.com"}, "To": [{"Address": "assistenza@buby.it"}], "Subject": "Fuori sede", "Created": "2026-11-14T10:02:00Z"},
            {"ID": "D", "MessageID": "d@x", "From": {"Address": "noreply@buby.it"}, "To": [{"Address": "assistenza@buby.it"}], "Subject": "Eco", "Created": "2026-11-14T10:03:00Z"},
        ]},
        "/api/v1/message/A/headers": {"In-Reply-To": ["<altro@x>"]},
        "/api/v1/message/A": {"Text": "Il freno stride", "Date": "2026-11-14T10:00:00Z"},
        "/api/v1/message/C/headers": {"Auto-Submitted": ["auto-replied"]},
    }
    monkeypatch.setattr(casella, "_get", lambda percorso: risposte[percorso])
    assert casella.leggi_casella(db) == 1                       # solo A: B e in uscita, C e automatica, D e nostra
    assert casella.leggi_casella(db) == 0                       # rilanciando non duplica
    s = db.query(Segnalazione).one()
    assert s.sede_id == 1 and s.testo == "Il freno stride" and s.in_reply_to == "altro@x"
