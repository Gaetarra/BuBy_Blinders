# Buby Rent

Applicazione web per noleggio di auto, furgoni ed e-bike (Laboratorio Integrato ITS, caso 3).

Stack: FastAPI, PostgreSQL, Docker Compose, autenticazione JWT, cifratura dei dati personali. Frontend: segnaposto, da sostituire con React.

## Avvio

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (documentazione interattiva su /docs)
- Frontend: http://localhost:3000

All'avvio le tabelle vengono create e caricati dati mock (2 sedi, 10 veicoli, 1 cliente, 2 utenti).

Genera una `SECRET_KEY` vera per firmare i token:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Autenticazione

Login con `POST /auth/login` (campi `username` = email e `password`), che restituisce un token JWT da inviare nell'header `Authorization: Bearer <token>`. Su `/docs` usa il pulsante Authorize.

Utenti di prova (cambia le password in `.env`):

| Ruolo | Email | Password |
| --- | --- | --- |
| admin | admin@buby.it | admin12345 |
| operatore (sede 1) | operatore@buby.it | operatore12345 |

I clienti si registrano con `POST /auth/register` (serve `accetta_privacy: true`).

## Email

In sviluppo la posta passa da Mailpit (http://localhost:8025): conferme di prenotazione e avvisi sulle segnalazioni partono dalla coda e arrivano lì. Un cliente che scrive a `assistenza@buby.it` (o `assistenza.torino@buby.it` per la sede) crea una segnalazione entro 15 secondi. Il servizio `worker` fa entrambe le cose. Dettagli in `DOCUMENTAZIONE.md`, sezione 9.

## Test

```bash
cd api && pip install -r requirements-dev.txt && pytest
```

## Import dei dati

I CSV vanno in `data/` (in `data/` ci sono tre file di esempio). Prima i veicoli, poi prenotazioni e segnalazioni:

```bash
docker compose exec api python -m app.import_csv veicoli /data/esempio_veicoli.csv
docker compose exec api python -m app.import_csv prenotazioni /data/esempio_prenotazioni.csv
docker compose exec api python -m app.import_csv segnalazioni /data/esempio_segnalazioni.csv
```

Il comando stampa le righe importate e quelle scartate con il motivo; si può rilanciare senza duplicare. Colonne e regole in `DOCUMENTAZIONE.md`, sezione 12.

## Protezione dei dati

Nome ed email dei clienti e l'email di login sono cifrati nel database (Fernet). La ricerca dell'email usa un'impronta HMAC con chiave separata. Le password sono hash bcrypt.

Imposta in `.env` chiavi vere (comandi in `.env.example`) e fanne un backup separato dal database: senza chiavi i dati non si recuperano. Se aggiorni da una versione precedente: `docker compose down -v`.

Endpoint GDPR: `GET /auth/me/dati` (esporta i propri dati), `PATCH /auth/me` (rettifica), `DELETE /auth/me` (cancella e anonimizza). Dettagli e checklist in `DOCUMENTAZIONE.md`, sezione 8.

## Struttura

```
api/app/main.py            avvio, CORS, router
api/app/models.py          tabelle e stati
api/app/availability.py    logica di disponibilita (sovrapposizione periodi)
api/app/security.py        hash password (bcrypt) e token JWT
api/app/deps.py            utente corrente e controllo dei ruoli
api/app/crypto.py          cifratura Fernet e impronta HMAC
api/app/encrypted_types.py colonna SQLAlchemy cifrata
api/app/rotate_keys.py     rotazione delle chiavi
api/app/import_csv.py      import da CSV
api/app/messaggi.py        da un messaggio a una segnalazione
api/app/casella.py         lettura della casella (Mailpit)
api/app/email_uscita.py    coda e invio delle email
api/app/worker.py          invia la coda, legge la casella
api/tests/                 test (pytest)
AGENTS.md                  istruzioni per gli agenti di codice
data/                      CSV di esempio
api/app/routers/           endpoint auth, veicoli e prenotazioni
api/app/seed.py            dati mock
frontend/public/           segnaposto frontend
```

## Da fare

- Tabelle Ispezione, Segnalazione, Manutenzione, Trasferimento (la manutenzione deve entrare nella disponibilita)
- Check-in e check-out
- Import dei dati del team DAI secondo il contratto dati
- Migrazioni con Alembic, test
- Frontend React
