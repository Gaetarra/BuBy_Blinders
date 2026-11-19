# AGENTS.md – Buby Rent

Istruzioni per gli agenti che lavorano su questo repository. Il progetto e la documentazione sono in italiano: mantenere nomi di dominio, stati e messaggi in italiano.

Fonti di verità, in ordine: questo file per i vincoli operativi, il codice in `buby-rent/`, `DOCUMENTAZIONE.md` per dominio/API/GDPR, `buby-rent/INTEGRAZIONE-FRONTEND-BACKEND.md` per frontend/API/Supabase e `docs/features/` per le singole feature. `.github/copilot-instructions.md` è un riassunto secondario e può essere meno aggiornato.

## 1. Contesto

- Applicazione di noleggio auto, furgoni ed e-bike su più sedi (caso 3 del Laboratorio Integrato ITS Academy ICT Piemonte).
- Ruoli: `cliente`, `operatore` (solo la propria sede), `ceo` (vista globale in sola lettura), `admin`.
- I dati sono sintetici, ma l'app va trattata come se fossero reali: cifratura, GDPR e permessi per ruolo.
- Il **20 novembre 2026** schema dati e contratto API vengono congelati; demo finale il 18 dicembre 2026. Dopo il congelamento solo modifiche additive, salvo richiesta esplicita.

## 2. Avvio e comandi

Tutti i comandi Docker si eseguono da `buby-rent/`. **Il file env è nella root del repository, non in `buby-rent/`.**

```bash
cd buby-rent
cp -n .env.example ../.env            # poi valorizza chiavi e password
docker compose --env-file ../.env up --build
docker compose --env-file ../.env down
docker compose --env-file ../.env down -v   # RESET del database
docker compose --env-file ../.env exec api python -m app.rotate_keys
docker compose --env-file ../.env logs -f worker
```

- Frontend React: `http://localhost:3000`; API e OpenAPI: `http://localhost:8000` e `/docs`; Mailpit: `http://localhost:8025`; pgAdmin (DB in sola lettura, per l'admin): `http://localhost:8080`.
- Il ruolo PostgreSQL di sola lettura usato da pgAdmin è creato dallo script `db/init/10-admin-readonly.sh`, montato in `docker-entrypoint-initdb.d`: viene eseguito alla prima inizializzazione del volume `pgdata`. Le sue credenziali sono `PGADMIN_RO_USER`/`PGADMIN_RO_PASSWORD`; l'accesso alla console usa `PGADMIN_DEFAULT_EMAIL`/`PGADMIN_DEFAULT_PASSWORD`. Su un volume già inizializzato il ruolo non viene ricreato: per cambiare la password serve un reset del volume o un `ALTER ROLE` manuale.
- Senza `--env-file ../.env`, Compose cerca `buby-rent/.env` (inesistente) e le variabili restano vuote.
- Le immagini si possono ricostruire senza toccare il volume. `down -v` serve solo per cambi di schema/chiavi, reset o modifica dei seed.
- Lo schema è creato da `Base.metadata.create_all()` all'avvio: **non ci sono migrazioni Alembic**. Dopo una modifica ai modelli ricreare il database.
- Il seed non aggiorna righe esistenti: cambiare `ADMIN_PASSWORD`/`OPERATORE_PASSWORD`/`CEO_PASSWORD` in `.env` non cambia le password già create (serve un reset del database).

## 3. Test e verifiche

```bash
# API: pytest con SQLite in memoria, senza PostgreSQL né Mailpit
docker build -f api/Dockerfile.test -t buby-rent-api-tests ./api
docker run --rm buby-rent-api-tests
docker run --rm buby-rent-api-tests python -m pytest -q tests/test_api.py::test_booking_overlap_returns_conflict

# In alternativa, senza Docker (dalla cartella api/)
pip install -r requirements-dev.txt && pytest
```

L'immagine `Dockerfile.test` copia il codice: ricostruiscila dopo ogni modifica, oppure usa pytest locale. I test Supabase sostituiscono JWKS e impostazioni con `monkeypatch` (fixture `supabase_identity` in `tests/conftest.py`): non devono chiamare la rete.

```bash
# Frontend (Bun + Node 22)
cd frontend
bun install --frozen-lockfile
bun run dev           # sviluppo locale
bun run test          # Vitest
bunx tsc --noEmit
bun run lint
```

Non coperti dai test: PostgreSQL reale, `SELECT ... FOR UPDATE` e concorrenza, Docker Compose, il worker con Mailpit reale, un progetto Supabase reale. Se tocchi queste parti, fai una prova manuale e dichiara nel resoconto cosa non hai verificato.

## 4. Struttura

```
buby-rent/api/app/
  main.py            bootstrap, CORS, logging richieste, router
  models.py          tabelle e costanti di stati/ruoli
  schemas.py         contratti Pydantic
  availability.py    unica logica di disponibilità dei veicoli
  operazioni.py      dashboard, comunicazioni, segnalazioni, manutenzioni, trasferimenti, check-in/out
  routers/           auth, veicoli, prenotazioni (non esiste un router segnalazioni)
  deps.py            autenticazione locale/Supabase e controllo ruoli
  supabase_auth.py   verifica JWT Supabase via JWKS
  crypto.py / encrypted_types.py / rotate_keys.py
  email_uscita.py    coda email; worker.py la spedisce
  import_csv.py      import da CSV; seed.py dati demo e utenti
buby-rent/frontend/  React 19 + TanStack Start; rotte in src/routes, client API in src/lib/api.ts
buby-rent/data/      CSV di esempio (veicoli, prenotazioni, segnalazioni)
buby-rent/db/        init del ruolo DB di sola lettura e configurazione pgAdmin
```

`frontend/src/routeTree.gen.ts` è generato: non modificarlo a mano. Le rotte sono file-based in `src/routes/`; non introdurre convenzioni Next.js/Remix.

`IDEE.md` nella root raccoglie le idee aperte di chiunque lavori al progetto: è un elenco leggero, non documentazione di dominio. Le priorità restano nel backlog (§ 9).

## 5. Regole non negoziabili

1. **Dati personali cifrati a livello applicativo.** Usa `StringaCifrata` (`encrypted_types.py`). Se il campo va cercato o reso unico, aggiungi una colonna `*_idx` con `blind_index()` ricalcolata in un `@validates`, come in `Cliente` e `Utente`. Mai `==` o ricerche SQL su un campo cifrato.
2. **Scritture solo tramite modelli SQLAlchemy.** Niente `INSERT`/`UPDATE` in SQL puro né `bulk_insert_mappings` su tabelle con campi cifrati: aggirano la cifratura.
3. **Niente dati personali nei log, negli errori o nei test con dati reali.** Il middleware registra solo metodo, path senza query, status, durata e tipo di errore. Non aggiungere body, header di autenticazione o messaggi di eccezione.
4. **Ogni endpoint dichiara chi può usarlo** con `Depends(utente_corrente)` o `Depends(richiedi_ruoli(...))`. I pubblici sono pochi e intenzionali: `/health`, `/auth/register`, `/auth/login`, `/veicoli/disponibili`. Il ruolo si legge dal database, mai dal token. Chi non ha permesso riceve `403`; una risorsa non visibile riceve `404` per non rivelarne l'esistenza.
5. **La disponibilità si calcola solo in `availability.py`.** Non duplicare la sovrapposizione (`inizio_A < fine_B` e `fine_A > inizio_B`). La creazione di una prenotazione deve mantenere `with_for_update()` per evitare doppie prenotazioni.
6. **Le email non si spediscono dalle richieste.** Chiama `accoda_email` (`email_uscita.py`) **prima del commit**, nella stessa transazione; il worker invia dopo. Non inviare direttamente da un handler.
7. **Input libero non fidato.** Testi di segnalazioni, note e comunicazioni non devono far scattare azioni (annullamenti, rimborsi, cambi di stato), nemmeno se letti da un'IA.
8. **Non introdurre altra infrastruttura** (k3s, microservizi, altri linguaggi o dipendenze) senza una ragione concreta. Lo stack è FastAPI + PostgreSQL + Compose + React/TanStack.
9. **Attenzione ai testi liberi non ancora cifrati:** `Segnalazione.testo`, `Ispezione.note`, `Manutenzione.descrizione`, `Trasferimento.note` sono `String`, non `StringaCifrata`. Non assumere che siano protetti; se aggiungi dati personali, cifrali e gestisci export/cancellazione.

## 6. Autenticazione, ruoli e Supabase

- Con `SUPABASE_URL` impostato, l'API verifica JWT Supabase ES256/RS256 (JWKS, issuer, audience, ruolo `authenticated`) e **disattiva** `/auth/login` e `/auth/register` locali con `410`. Il collegamento avviene con `POST /auth/supabase/provision` tramite `identita_supabase`; un token valido ma non collegato riceve `403`.
- Il backend usa `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY`. Il frontend usa `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY`, che Compose deriva dalle variabili backend. Impostare solo le `VITE_*` nel `.env` non abilita Supabase nell'API.
- Mai usare una secret/service-role key nel bundle browser: solo la chiave publishable.
- `ceo` è in sola lettura; `admin` deve indicare `sede_id` nelle viste globali; l'operatore è sempre limitato alla propria sede lato server. Il filtro frontend non è una misura di sicurezza.
- **L'admin accede al database solo in sola lettura**, tramite pgAdmin e il ruolo `PGADMIN_RO_USER` (solo `SELECT`). Non ha credenziali superuser, non scrive da SQL e le modifiche ai dati passano dalle API, che applicano cifratura e permessi. Non allargare questi permessi senza una richiesta esplicita.
- **Comunicazioni interne:** operatori, admin e CEO vedono la scheda. L'operatore vede la propria sede e le note non smistate, crea note per la propria sede e prende in carico; l'admin crea e assegna a qualsiasi operatore; il CEO legge soltanto. Il filtro per sede va mantenuto lato API.
- Il JWT del frontend resta in memoria (`src/lib/auth.ts`), non in `localStorage`. La sessione non sopravvive al reload.
- In Compose il frontend viene compilato con gli `ARG` `VITE_*`: cambiare queste variabili richiede un rebuild.

## 7. Convenzioni

- Dominio, tabelle, campi, stati e messaggi in italiano; solo l'infrastruttura segue i nomi inglesi delle librerie.
- Usa le costanti di `models.py` (`STATI_VEICOLO`, `STATI_PRENOTAZIONE`, `RUOLI`, ...) e validale negli schemi Pydantic.
- Datetime senza fuso orario, in UTC.
- Codici HTTP: `401` non autenticato, `403` ruolo insufficiente, `404` non trovato/non visibile, `409` conflitto, `422` dati non validi.
- Aggiorna nello stesso intervento `DOCUMENTAZIONE.md` (tabella API, modello dati), `README.md` e `.env.example` quando cambiano setup o comportamento.
- Per modifiche a schema, query o Supabase consulta prima `.agents/skills/supabase/SKILL.md` e `.agents/skills/supabase-postgres-best-practices/SKILL.md`.
- Il frontend è collegato a Lovable: non riscrivere storia già pubblicata (force push, rebase/amend di commit pushati) e non modificare file generati o `supabase/migrations/`. Vedi `frontend/AGENTS.md`.

## 8. Trappole verificate

- `rotate_keys.CAMPI_CIFRATI` copre oggi solo `Cliente` e `Utente`; `ComunicazioneInterna.testo` e i campi di `EmailDaInviare` sono cifrati ma non vengono ricifrati dalla rotazione. Aggiungi ogni nuovo campo cifrato a `CAMPI_CIFRATI`.
- `README.md` dichiara ancora «2 sedi, 10 veicoli, 1 cliente, 2 utenti», ma `seed.py` crea 6 sedi, 48 veicoli, 12 clienti e più operatori/CEO. Fai fede al codice.
- L'import CSV va eseguito nell'ordine `veicoli` → `prenotazioni` → `segnalazioni`, perché le righe successive cercano targhe ed email già presenti.
- `logs/api.log` è gitignorato e montato in Compose; non committarlo e non usarlo per dati personali.
- Il worker non crea i dati demo: il seed avviene all'avvio dell'API.

## 9. Backlog (priorità)

1. Gestione utenti da parte dell'admin (creare operatori, cambiare ruoli).
2. Includere manutenzioni e trasferimenti pianificati nel calcolo della disponibilità; upload/conservazione sicura delle foto.
3. Import di previsioni/KPI del team DAI secondo il contratto dati; pseudonimizzazione dei dati consegnati.
4. Migrazioni Alembic al posto di `create_all`; ampliare la copertura test.
5. Completare l'area cliente e i flussi operatore nel frontend React.
6. Retention, audit nominativo degli accessi, verifica email, lettore IMAP/provider al posto di Mailpit.

## 10. Definition of done

I test passano; ogni nuovo endpoint ha autenticazione e test di permesso; ogni nuovo campo personale è cifrato e incluso in export, cancellazione e rotazione; nessun dato personale nei log; documentazione aggiornata; nel resoconto dichiari cosa hai verificato e cosa no (PostgreSQL, Docker, Mailpit, Supabase reale).
