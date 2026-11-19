# Integrazione frontend e backend

## Scopo

Collegare il frontend React/TanStack aggiunto da Lovable all'API FastAPI esistente e rendere riproducibili build e avvio con Docker Compose, mantenendo compatibili l'autenticazione locale e quella Supabase.

## Implementazione

### Frontend

- Il login usa l'API FastAPI locale quando Supabase non e' configurato.
- Quando sono configurate `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY`, il login usa Supabase Auth, invia il JWT a `POST /auth/supabase/provision` e usa poi quel token per le richieste API.
- La sessione viene mantenuta in memoria, non in `localStorage`. Il client Supabase rinnova il token; dopo un refresh della pagina l'utente deve autenticarsi nuovamente.
- Le richieste API includono il token Bearer e gestiscono gli errori HTTP e di rete.
- La dashboard staff consuma profilo, prenotazioni, flotta e modifica stato veicolo. Gli utenti cliente vedono invece il proprio elenco prenotazioni.
- I dati demo restano disponibili separatamente per visualizzare la dashboard senza autenticarsi.
- L'interfaccia precedente e' conservata in `frontend/public/legacy.html`; non e' piu' l'entrypoint servito.

### API e autorizzazioni

- L'API verifica i JWT Supabase asimmetrici (ES256/RS256), issuer, audience, scadenza e ruolo `authenticated` usando il JWKS del progetto.
- `POST /auth/supabase/provision` collega l'identita' Supabase all'utente locale tramite UUID e email verificata. Per i clienti nuovi richiede consenso privacy e nome.
- La tabella `identita_supabase` associa l'UUID Supabase all'utente applicativo. Ruolo e sede sono sempre letti dal database, non dai claim applicativi del token.
- Con Supabase attivo, login e registrazione locali vengono disabilitati. Se Supabase non e' configurato, rimane attivo il login JWT locale.
- La cancellazione dell'account cliente elimina anche il collegamento all'identita' Supabase.
- CORS accetta origini esplicite tramite `CORS_ORIGINS`; il wildcard `*` viene rifiutato.

### Docker

- `frontend/Dockerfile` usa Bun per installare dipendenze e compilare, poi Node.js 22 per eseguire il server Nitro `node-server`.
- `frontend/vite.config.ts` seleziona il preset Nitro `node-server`, compatibile con il runtime container.
- Compose costruisce il frontend dall'app React; non monta piu' la vecchia pagina HTML come applicazione principale.
- Il servizio API ha un health check HTTP; il frontend parte dopo che l'API e' healthy.
- L'immagine runtime API non avvia il reloader; Compose lo abilita per lo sviluppo.
- Il volume PostgreSQL esistente e' stato preservato durante la ricostruzione.

## Configurazione

Il file env usato in questo ambiente e' `../.env` rispetto a `buby-rent/`; non versionarlo e non copiarne i valori nella documentazione.

Per l'accesso locale:

```env
VITE_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

Per abilitare Supabase, valorizzare inoltre `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY`. La chiave publishable viene incorporata nel bundle browser ed e' pubblica per definizione: non usare una service-role key. Per il preview Lovable remoto, `VITE_API_URL` deve puntare a un'API pubblica HTTPS e `CORS_ORIGINS` deve contenere l'origine esatta del preview. `localhost` nel browser remoto indica il computer dell'utente, non il computer che esegue Compose.

Avvio o ricostruzione, dalla cartella `buby-rent/`:

```bash
docker compose --env-file ../.env up --build -d
```

- Frontend: `http://localhost:3000/login`
- API e OpenAPI: `http://localhost:8000` e `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

Non serve cancellare il volume database per ricostruire le immagini. Evitare `docker compose down -v` salvo richiesta esplicita di reset del database.

## Verifiche eseguite

- Build dell'immagine API e dell'immagine React/Nitro.
- Compose validato con `docker compose --env-file ../.env config --quiet`.
- API: 12 test pytest superati.
- Frontend: 4 test Vitest superati, `tsc --noEmit` e lint dei file modificati superati.
- API e frontend healthy dopo l'avvio Compose.
- Verificato nel browser che `/login` mostra il form React e che la dashboard viene renderizzata.
- Verificati CORS, login locale, profilo, dashboard flotta e prenotazioni via API.

## Limiti noti

- Al momento della verifica `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` non erano configurati nel `.env`: il flusso Supabase e' implementato, ma in locale e' stato verificato il login FastAPI, non un login reale contro Supabase.
- Gli account Supabase admin/operatori devono avere la stessa email verificata dell'account applicativo preesistente.
- Il frontend non include ancora il flusso per registrare un nuovo cliente con nome e consenso privacy.
- La sessione in memoria non sopravvive al ricaricamento della pagina.
- Per rendere accessibile l'app Lovable da un browser remoto occorre pubblicare l'API dietro HTTPS e configurare le origini CORS corrette.

## Aggiornamenti successivi

Nel branch sono state aggiunte anche le skill operative per lavorare in modo coerente
con Supabase e PostgreSQL:

- le istruzioni Supabase definiscono il flusso di autenticazione, provisioning,
  gestione delle sessioni e separazione tra chiavi pubbliche e segreti;
- le best practice PostgreSQL raccolgono linee guida per schema, vincoli,
  chiavi esterne, indici, transazioni, locking, pooling, RLS e analisi delle
  prestazioni;
- le linee guida sono disponibili nelle skill locali sotto `.agents/skills/` e
  devono essere consultate prima di modificare schema, query o configurazione
  Supabase/PostgreSQL.

Queste aggiunte riguardano il processo di sviluppo e non introducono una
migrazione automatica del database: lo schema applicativo continua a essere
creato all'avvio da SQLAlchemy tramite `Base.metadata.create_all()`, come
descritto in [DOCUMENTAZIONE.md](../DOCUMENTAZIONE.md).
