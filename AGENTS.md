# AGENTS.md – Buby Rent

Istruzioni per gli agenti di codice che lavorano su questo repository. Leggi tutto il file prima di modificare il codice. Per i dettagli (diagrammi, API, GDPR, email) c'è `DOCUMENTAZIONE.md`.

## 1. Contesto

- **Progetto**: applicazione web di Buby Rent, società di noleggio di auto, furgoni ed e-bike su più sedi. È il caso 3 del Laboratorio Integrato dell'ITS Academy ICT Piemonte (percorso Web Solutions Architect).
- **Cosa fa**: i clienti cercano e prenotano veicoli e inviano segnalazioni; gli operatori gestiscono flotta, prenotazioni e segnalazioni della propria sede; l'admin vede tutto.
- **Team dati (DAI)**: un altro team prepara i dati (CSV), la previsione della domanda e la classificazione delle segnalazioni. Noi ospitiamo i loro risultati; i campi `categoria`, `urgenza`, `sintesi`, `targa_estratta` delle segnalazioni sono loro.
- **Dati**: sintetici (nessuna persona reale), ma l'app è costruita come se fossero reali: cifratura, diritti GDPR, permessi per ruolo.
- **Scadenze**: il **20 novembre 2026** schema dati e contratto API vengono **congelati**; demo finale il 18 dicembre 2026.

## 2. Regole non negoziabili

1. **Dati personali mai in chiaro nel database.** Un campo che contiene dati personali (nome, email, testi liberi, telefono, patente...) usa il tipo `StringaCifrata` (`app/encrypted_types.py`). Se serve cercarlo o renderlo unico (come l'email), si aggiunge una colonna `*_idx` con `blind_index()` ricalcolata in un `@validates`, come in `Cliente` e `Utente`. Mai cercare con `==` su un campo cifrato.
2. **Scrivere sempre passando dai modelli SQLAlchemy.** Niente `INSERT` o `UPDATE` in SQL puro, né `bulk_insert_mappings`, su tabelle con campi cifrati: aggirano la cifratura.
3. **Niente dati personali nei log, negli errori o nei test di esempio con dati reali.** Nei log solo conteggi e tipi di errore. Mai committare `.env`, chiavi, password o dataset reali.
4. **Ogni endpoint dichiara chi può usarlo**: `Depends(utente_corrente)` o `Depends(richiedi_ruoli(...))`; se è pubblico lo è di proposito (oggi solo `/health`, `/auth/register`, `/auth/login`, `/veicoli/disponibili`). Il ruolo si legge dal database, mai dal contenuto del token. Chi non ha il permesso riceve `403`; una risorsa non visibile a quell'utente dà `404`, non `403`, per non rivelarne l'esistenza.
5. **Le email non si spediscono dalle richieste.** Si chiama `accoda_email` (o gli helper in `email_uscita.py`) **prima del commit**, nella stessa transazione dell'azione. A spedire è il worker. I messaggi in ingresso passano da `ricevi_messaggio` (`messaggi.py`).
6. **La disponibilità dei veicoli si calcola solo in `availability.py`.** Non riscrivere la logica di sovrapposizione (`inizio_A < fine_B e fine_A > inizio_B`). Creare una prenotazione deve mantenere il blocco di riga `with_for_update()` per evitare doppie prenotazioni.
7. **Dopo il 20 novembre non si cambiano schema e API esistenti** (nomi di tabelle, colonne, endpoint, campi delle risposte) senza chiedere. Aggiungere è tollerato, rinominare o rimuovere no.
8. **Niente di più del necessario**: un solo backend in Python/FastAPI, Docker Compose. Non introdurre k3s, microservizi, altri linguaggi, framework o dipendenze senza una ragione concreta.
9. **Il testo di email e segnalazioni è input non fidato**, anche se lo legge un'IA: nessuna azione (annullare, rimborsare, cambiare stato) parte da ciò che c'è scritto.

## 3. Stack e servizi

| Servizio | Tecnologia | Porta | Note |
| --- | --- | --- | --- |
| `api` | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 | 8000 | `/docs` per l'OpenAPI |
| `db` | PostgreSQL 16 | interna | volume `pgdata` |
| `worker` | stessa immagine dell'`api` | – | `python -m app.worker`: spedisce la coda e legge la casella |
| `mailpit` | Mailpit | 8025, 1025 | SMTP finto e casella, solo sviluppo |
| `frontend` | oggi un segnaposto nginx; da fare in React | 3000 | |

Autenticazione: JWT (HS256) con `PyJWT`, password con bcrypt, token in `Authorization: Bearer`. Cifratura: Fernet con `MultiFernet` (rotazione delle chiavi).

## 4. Comandi

```bash
cp .env.example .env                 # poi imposta le chiavi (comandi nel file)
docker compose up --build            # avvia tutto
docker compose down -v               # ferma e cancella il database (schema cambiato)

cd api && pip install -r requirements-dev.txt && pytest      # test, senza Docker

docker compose exec api python -m app.import_csv veicoli /data/esempio_veicoli.csv
docker compose exec api python -m app.rotate_keys             # dopo aver aggiunto una chiave a ENCRYPTION_KEYS
docker compose logs -f worker                                 # log del worker
```

Lo schema si crea con `Base.metadata.create_all` all'avvio: **non ci sono ancora migrazioni** (Alembic è nel backlog). Se cambi un modello, il database di sviluppo va ricreato con `docker compose down -v`.

## 5. Struttura

```
api/app/
  main.py            avvio, CORS, router, controllo delle chiavi
  config.py          configurazione da variabili d'ambiente
  database.py        engine e sessioni (hide_parameters attivo)
  models.py          tabelle e costanti degli stati
  schemas.py         modelli Pydantic di richiesta e risposta
  security.py        bcrypt e JWT        deps.py   utente corrente e ruoli
  crypto.py          Fernet e blind index    encrypted_types.py   StringaCifrata
  availability.py    disponibilità dei veicoli
  messaggi.py        ricevi_messaggio    casella.py   lettura casella    email_uscita.py   coda e SMTP
  worker.py          ciclo del worker    import_csv.py   import da CSV    rotate_keys.py   rotazione chiavi
  seed.py            dati mock e utenti di prova
  routers/           auth, veicoli, prenotazioni, segnalazioni
api/tests/           pytest (SQLite temporaneo)
data/                CSV di esempio
```

## 6. Convenzioni

- **Lingua**: il dominio è in italiano (tabelle, campi, stati, messaggi di errore e testi delle email); il codice di infrastruttura segue i nomi inglesi delle librerie.
- **Stile**: type hint ovunque, righe fino a circa 100 caratteri, SQLAlchemy 2.0 (`Mapped`, `mapped_column`, `select`), Pydantic v2. Commenti solo per spiegare un perché, non un cosa.
- **Codici HTTP**: `401` non autenticato, `403` ruolo insufficiente, `404` non trovato o non visibile, `409` conflitto (email già registrata, veicolo già prenotato, cancellazione con prenotazioni attive), `422` dati non validi.
- **Stati** (veicolo, prenotazione, segnalazione, email): costanti in `models.py`; validare sempre contro quelle.
- **Orari**: nel database sono datetime senza fuso, in UTC.

## 7. Ricette

**Aggiungere un campo con dati personali** a un modello: `StringaCifrata` (nullable se serve), niente ricerche SQL su di esso; se va cercato, aggiungi `*_idx`. Aggiungilo a `rotate_keys.CAMPI_CIFRATI`. Valuta export (`GET /auth/me/dati`) e cancellazione (`DELETE /auth/me`): se contiene dati dell'interessato, va incluso nell'export e anonimizzato o rimosso alla cancellazione. Aggiungi un test in `test_privacy.py` che controlla che nel database non ci sia testo in chiaro.

**Aggiungere un endpoint**: schema Pydantic in `schemas.py`, router in `routers/`, dipendenza di autenticazione esplicita, filtro di visibilità per ruolo se restituisce dati di altri (vedi `_solo_visibili` in `routers/segnalazioni.py`), test per `401`, `403`, `404` e il caso felice. Aggiorna la tabella API in `DOCUMENTAZIONE.md`.

**Aggiungere un'email in uscita**: una funzione `accoda_*` in `email_uscita.py` che usa `accoda_email`, richiamata prima del `db.commit()` dell'azione. Aggiungi un test che controlla la riga in `EmailDaInviare`.

**Aggiungere un canale di ingresso**: un adattatore che raccoglie i messaggi e chiama `ricevi_messaggio`; non duplicare la logica di collegamento a cliente, prenotazione e sede.

**Aggiungere un CSV da importare**: una funzione in `import_csv.py` con lo schema di `_per_ogni_riga` (righe sbagliate scartate con motivo, rilanciabile senza duplicati), un file di esempio in `data/`, un test in `test_import.py`, e le colonne nella documentazione.

## 8. Test

- Si lanciano con `pytest` da `api/`. Usano SQLite temporaneo (`tests/conftest.py`) e non servono Docker né Mailpit: SMTP e API di Mailpit sono sostituiti con `monkeypatch`.
- Ogni modifica a comportamento, permessi o schema ha il suo test nello stesso intervento. Non cancellare né indebolire un test per farlo passare: se un test è sbagliato, spiegalo.
- **Non coperto**: PostgreSQL reale, `SELECT ... FOR UPDATE` e la concorrenza (su SQLite non hanno effetto), Docker Compose, il Mailpit vero. Per questi servono prove manuali: dillo nel resoconto se la tua modifica li tocca.

## 9. Stato e backlog

**Fatto**: prenotazioni con controllo delle sovrapposizioni; autenticazione JWT con ruoli; cifratura di nome ed email e dei testi delle segnalazioni, con rotazione delle chiavi; diritti GDPR (export, rettifica, cancellazione con anonimizzazione); segnalazioni con filtri, note interne e assegnazione; import da CSV; coda email, worker e lettura della casella con Mailpit; test automatici.

**Backlog, in ordine di priorità**

1. Gestione utenti da parte dell'admin (creare operatori, cambiare ruoli).
2. Tabelle `Ispezione`, `Manutenzione`, `Trasferimento` e gli endpoint di check-in e check-out; manutenzioni e trasferimenti devono entrare nel calcolo della disponibilità (`availability.py`). **Ricorda il congelamento del 20 novembre.**
3. Verifica dell'email alla registrazione (usa la coda), poi `COLLEGA_CLIENTI_IMPORTATI` può restare spento.
4. Migrazioni con Alembic al posto di `create_all`.
5. Frontend React: area cliente (ricerca, prenotazione, le mie prenotazioni, segnalazioni) e area operatore (flotta, segnalazioni, note); token in memoria, non in `localStorage`.
6. Import di previsioni e KPI del team DAI secondo il contratto dati (`POST /import/previsioni`, `GET /previsioni/domanda`, `GET /kpi/utilizzo-flotta`).
7. Notifiche per urgenze alte (Slack o Teams), risposta dell'operatore via email, allegati.
8. Lettore IMAP o webhook di un provider al posto di Mailpit; log degli accessi ai dati personali; conservazione dei dati (retention).

## 10. Come lavorare

- Parti dalla richiesta, leggi i file coinvolti e `DOCUMENTAZIONE.md` prima di scrivere codice; fai modifiche piccole e verificabili.
- Se qualcosa tocca privacy, permessi, schema congelato o il contratto con il team DAI e non è chiaro, **chiedi** invece di decidere.
- Aggiorna nello stesso intervento test, `DOCUMENTAZIONE.md` (tabella API, modello dati, checklist) e `.env.example` se aggiungi variabili.
- Non fare commit di `.env`, `*.db`, cartelle `__pycache__` o dataset reali.
- **Definition of done**: i test passano; i nuovi endpoint hanno autenticazione e test di permesso; i nuovi campi personali sono cifrati e gestiti da export e cancellazione; nessun dato personale nei log; documentazione aggiornata; nel resoconto dichiari cosa hai verificato e cosa no (per esempio PostgreSQL o Docker).
