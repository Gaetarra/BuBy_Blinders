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
