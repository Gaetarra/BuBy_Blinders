# Buby Rent

Applicazione web per noleggio di auto, furgoni ed e-bike (Laboratorio Integrato ITS, caso 3).

Stack: FastAPI, PostgreSQL, Docker Compose e frontend React/TanStack generato con Lovable, compilato e servito con Nitro su Node.js.

Per i dettagli dell'integrazione frontend/API, autenticazione e container, vedi [INTEGRAZIONE-FRONTEND-BACKEND.md](./INTEGRAZIONE-FRONTEND-BACKEND.md).

## Avvio

```bash
cp -n .env.example ../.env
# Imposta i valori reali richiesti nel file ../.env.
docker compose --env-file ../.env up --build
```

- Frontend React: http://localhost:3000
- API: http://localhost:8000 (documentazione interattiva su /docs)
- Health check: http://localhost:8000/health
- Mailpit: http://localhost:8025

Le conferme delle prenotazioni vengono accodate dal backend e spedite dal
worker tramite Mailpit. Il worker è un servizio separato del compose e non
blocca le richieste API se il server SMTP non è disponibile.

Le date mostrate al cliente, all'operatore e nelle email usano il formato
italiano leggibile `GG/MM/AAAA alle HH:MM`; le API continuano a usare ISO 8601.

La dashboard include anche le comunicazioni interne: le note sono cifrate,
non vengono esposte nell'area cliente e possono essere collegate a un veicolo,
assegnate a un operatore e smistate per sede. Un operatore vede le note della
propria sede e quelle ancora non smistate; admin e CEO possono consultare la
vista globale, mentre solo admin e operatori possono creare o prendere in
carico una comunicazione.

La documentazione separata delle feature è disponibile in
[`../docs/features/`](../docs/features/README.md).

Per importare i CSV di esempio, eseguire nell'ordine:

```bash
docker compose exec api python -m app.import_csv veicoli /data/esempio_veicoli.csv
docker compose exec api python -m app.import_csv prenotazioni /data/esempio_prenotazioni.csv
docker compose exec api python -m app.import_csv segnalazioni /data/esempio_segnalazioni.csv
```
- Log API: `buby-rent/logs/api.log` (rotazione automatica a 10 MB, conserva 5 file)

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
| operatore Porta Susa | operatore.porta-susa@buby.it | operatore12345 |
| operatore Lingotto | operatore.lingotto@buby.it | operatore12345 |
| operatore Moncalieri | operatore.moncalieri@buby.it | operatore12345 |
| operatore Rivoli | operatore.rivoli@buby.it | operatore12345 |
| operatore Venaria Reale | operatore.venaria-reale@buby.it | operatore12345 |
| CEO (tutte le sedi, sola lettura) | buby@buby.it | buby12345 |

I clienti si registrano con `POST /auth/register` (serve `accetta_privacy: true`).

## Collegamento frontend/API e Supabase Auth

Il frontend usa gli endpoint FastAPI per login, profilo, prenotazioni, dashboard e aggiornamento dello stato dei veicoli. In Compose `VITE_API_URL` predefinito è `http://localhost:8000`; l'API consente l'origine frontend locale `http://localhost:3000` tramite CORS.

Per abilitare l'accesso Supabase, imposta `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` nel file env passato a Compose (`../.env` nell'esempio sopra), quindi ricostruisci i servizi:

```bash
docker compose --env-file ../.env up --build -d
```

La chiave publishable è inserita nel bundle browser ed è pubblica per definizione: non usare mai una secret/service-role key. Con `SUPABASE_URL` configurato, il frontend autentica con Supabase, collega la sessione a `POST /auth/supabase/provision` e invia il JWT Supabase alle rotte API; login e registrazione locali vengono disattivati dal backend. Senza configurazione Supabase, resta disponibile il login locale FastAPI. Il JWT resta in memoria nel browser, non in `localStorage`.

Per collegare un admin/operatore esistente, crea in Supabase un utente con la stessa email verificata dell'account applicativo già provisionato. Un nuovo profilo cliente richiede nome e consenso privacy: il flusso di registrazione frontend non è ancora implementato.

Per usare Lovable al di fuori della rete locale, configura `VITE_API_URL` con l'URL pubblico HTTPS dell'API e aggiungi l'origine esatta del frontend a `CORS_ORIGINS`. Se il frontend è compilato con Supabase, imposta `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY` nell'ambiente di build Lovable; non inserire segreti nel bundle.

## Protezione dei dati

Nome ed email dei clienti e l'email di login sono cifrati nel database (Fernet). La ricerca dell'email usa un'impronta HMAC con chiave separata. Le password sono hash bcrypt.

Imposta in `.env` chiavi vere (comandi in `.env.example`) e fanne un backup separato dal database: senza chiavi i dati non si recuperano. Se aggiorni da una versione precedente: `docker compose down -v`.

Endpoint GDPR: `GET /auth/me/dati` (esporta i propri dati), `PATCH /auth/me` (rettifica), `DELETE /auth/me` (cancella e anonimizza). Dettagli e checklist in `DOCUMENTAZIONE.md`, sezione 8.

## Funzioni operative

Gli operatori possono usare la dashboard per sede per filtrare la flotta e le prenotazioni attive, registrare check-in/check-out con i dati d'ispezione, e gestire segnalazioni, manutenzioni e trasferimenti. Gli operatori vedono solo la propria sede; gli admin selezionano la sede.

Il campo foto delle ispezioni accetta attualmente un URL. L'upload e la conservazione dei file non sono ancora implementati. API e codici di risposta sono descritti in `../DOCUMENTAZIONE.md`, sezione 9.

## Test API

I test usano un database SQLite temporaneo e dati fittizi, senza toccare il database di sviluppo:

```bash
cd buby-rent
docker build -f api/Dockerfile.test -t buby-rent-api-tests ./api
docker run --rm buby-rent-api-tests
```

Per eseguire un singolo test:

```bash
docker run --rm buby-rent-api-tests python -m pytest -q tests/test_api.py::test_booking_overlap_returns_conflict
```

I test coprono login e autorizzazioni, verifica e provisioning Supabase, collegamento/cancellazione account, privacy dei log, prenotazioni/sovrapposizioni, dashboard per sede e check-in/check-out.

Il frontend ha test Vitest e controllo TypeScript. Per eseguirli senza installare Bun sul computer:

```bash
docker run --rm \
  --volume "$PWD/frontend:/app" \
  --volume /app/node_modules \
  --workdir /app \
  oven/bun:1-alpine \
  sh -c 'bun install --frozen-lockfile && bun run test && bunx tsc --noEmit'
```

## Log delle richieste API

Ogni richiesta API produce una riga in `logs/api.log` con ID richiesta, metodo, percorso (senza query string), status HTTP, durata e tipo di errore non gestito se presente. Le risposte 4xx sono registrate come warning e le 5xx come errori. Il log è persistente sul filesystem del progetto, ruota a 10 MB e mantiene cinque file precedenti.

Per correlare una risposta del browser con il log, usa l'header `X-Request-ID`. Per evitare di esporre dati personali o credenziali, i log non includono body, header di autenticazione, query string o dettagli delle eccezioni.

Per seguire il log mentre l'applicazione è in esecuzione:

```bash
tail -f logs/api.log
```

## Struttura

```
api/app/main.py            avvio, CORS, router
api/app/models.py          tabelle e stati
api/app/availability.py    logica di disponibilita (sovrapposizione periodi)
api/app/operazioni.py      dashboard flotta, ispezioni e operazioni di sede
api/app/security.py        hash password (bcrypt) e token JWT
api/app/deps.py            utente corrente e controllo dei ruoli
api/app/crypto.py          cifratura Fernet e impronta HMAC
api/app/encrypted_types.py colonna SQLAlchemy cifrata
api/app/rotate_keys.py     rotazione delle chiavi
api/app/routers/           endpoint auth, veicoli e prenotazioni
api/app/seed.py            dati mock
frontend/src/               frontend React/TanStack con dashboard, login e client API
frontend/public/legacy.html interfaccia HTML precedente conservata
```

## Da fare

- Upload sicuro delle foto e verifica temporale di manutenzioni/trasferimenti nella disponibilita
- Import dei dati del team DAI secondo il contratto dati
- Migrazioni con Alembic e ampliamento della copertura dei test
- Frontend React e completamento dell'area cliente
