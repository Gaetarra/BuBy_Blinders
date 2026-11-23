# Verifica dei requisiti della consegna

**Data:** 23 novembre 2026
**Fonti:** `Consegna progetto informazioni.md`, `AGENTS.md`, `DOCUMENTAZIONE.md`, `dai/README.md`, codice in `buby-rent/` e `dai/`, stack in esecuzione.

## Metodo

1. Estratti i requisiti dalla traccia (obiettivo tecnico, attività per corso, calendario, criteri di valutazione).
2. Confrontati con lo stato reale del repository e con l'applicazione in esecuzione.
3. Prove eseguite:
   - login e navigazione nel browser con 6 operatori e CEO (vedi `prove-accesso.md`);
   - controlli di autorizzazione su 31 operazioni API;
   - import dei tre CSV del team DAI in un database SQLite temporaneo con l'importatore dell'app;
   - `pytest` API, `vitest` frontend, `tsc --noEmit`, `eslint`.

Non sono state verificate: concorrenza su PostgreSQL reale, invio email con Mailpit reale, Supabase reale, deploy, HTTPS.

## Matrice dei requisiti

| # | Requisito della traccia | Esito | Evidenza |
| --- | --- | --- | --- |
| R1 | Dati strutturati e non strutturati puliti, documentati, nel formato concordato (schema, formato API, esempi di risposta) | **Parziale** | Pipeline `dai/` notebook 01–04 e `export_app/` verificati: 64 veicoli, 4.905 prenotazioni, 1.388 segnalazioni importate con **0 scarti**. Mancano dizionario dei dati, documento unico di contratto e pseudonimizzazione; le 5 sedi DAI non coincidono con le 6 sedi dell'app. |
| R2 | Almeno una componente di analisi (KPI del caso) | **Mancante** | Nessun KPI calcolato né esportato. `dai/README.md` §8: “KPI” non spuntato. In dashboard il grafico “Domanda prevista” è mock (A2). |
| R3 | Almeno una componente di elaborazione testi/email (classificazione, estrazione, sintesi) | **Mancante** | Nessun notebook o modello di classificazione. `segnalazioni.csv` ha le colonne di classificazione vuote: importandolo, **tutte le 1.388 segnalazioni** prendono la categoria predefinita `guasto`. |
| R4 | Applicazione web funzionante con database, API, interfaccia (dashboard, ricerca, visualizzazioni) che usa i dati reali del team dati | **Parziale** | App funzionante: 31 operazioni API, ruoli corretti, 13 test API verdi, dashboard e filtro flotta. Ma l'istanza demo contiene solo il seed (12 prenotazioni), non i dati DAI; il frontend ha solo login e dashboard, senza area cliente né flussi operatore. |
| R5 | Documentazione tecnica (architettura, API) | **Parziale** | `DOCUMENTAZIONE.md` è ampia (architettura, modello dati, API, GDPR), ma ha disallineamenti: tabella API incompleta, ruoli errati su `/dashboard/flotta`, descrizione della sessione superata. |
| R6 | Repository del codice e istruzioni di installazione | **Parziale** | Repo e `README.md` con `docker compose`, `.env.example` completo. Il README riporta ancora “2 sedi, 10 veicoli, 1 cliente, 2 utenti” (riga 49); nessuna CI, nessun deploy. |
| R7 | Demo finale davanti all'azienda | **Da fare** | Prevista il 18/12/2026. |
| R8 | GDPR, anonimizzazione, NDA e uso responsabile dell'AI | **Parziale** | Cifratura nome/email con blind index, diritti 15–17/20, export e cancellazione, checklist in `DOCUMENTAZIONE.md` §8.4. Restano da fare retention, log accessi, informativa, registro dei trattamenti, NDA, pseudonimizzazione dei dati per DAI e cifratura dei testi liberi. |
| R9 | Rispetto delle scadenze (SAL 1 del 20/11 con congelamento) | **Rispettato per ora** | Ultimo commit il 19/11: nessuna modifica dopo il congelamento. Non c'è ancora nulla da verificare sulla regola “solo additivo”. |
| R10 | WSA: architettura, backend con auth, frontend, integrazione, test e rilascio | **Parziale** | Architettura e backend solidi, autorizzazioni verificate; frontend incompleto; integrazione dati DAI solo potenziale; rilascio assente. |
| R11 | Criteri comuni: collaborazione, chiarezza documentazione, efficacia demo | **Parziale** | Documentazione ricca ma con drift; demo a rischio per i punti P0 sotto. |

## Dettaglio per area

### Dati e contratto (R1)

Fatto e verificato il 23/11:

```text
veicoli.csv        -> Importate: 64    Saltate: 0
prenotazioni.csv   -> Importate: 4905  Saltate: 0
segnalazioni.csv   -> Importate: 1388  Saltate: 0
```

Problemi aperti:

- **Dizionario dei dati assente** (`dai/README.md` §8).
- **Contratto non è un documento unico**: schema e formati sono divisi tra `DOCUMENTAZIONE.md` §9, `dai/README.md` §6 e `import_csv.py`.
- **Sedi incoerenti**: i CSV DAI creano 5 sedi (Torino Lingotto, Alba, Bardonecchia, Stresa, Casale Monferrato), il database dell'app ne ha 6 (Torino Centro, Porta Susa, Lingotto, Moncalieri, Rivoli, Venaria Reale). Importando i CSV nell'istanza attuale si ottengono 11 sedi. È la domanda aperta n. 3 di `dai/README.md` §6.
- **Classificazione vuota**: `categoria`, `urgenza`, `sintesi`, `targa_estratta` non sono compilate; l'import assegna `guasto` a tutto.
- **Pseudonimizzazione non fatta**: gli export contengono nome ed email del cliente.

### Analisi e AI (R2, R3)

- KPI: nessun file o notebook. La dashboard mostra una previsione statica presa da `demo.ts`, con sedi inesistenti.
- Previsione della domanda: non presente.
- Classificazione dei messaggi: non presente; il dataset è pulito ma non etichettato.
- Report dei risultati e slide: non presenti.
- Uso responsabile AI: le regole sono scritte in `dai/README.md` §5 ma non c'è ancora una componente da valutare.

### Applicazione (R4, R10)

- API: 31 operazioni, ruoli e sedi corretti (operatore limitato alla sede, CEO in sola lettura, admin obbligato a indicare la sede, 401/403/422 coerenti).
- Test: **13 test API verdi**; **1 test frontend verde**; `tsc --noEmit` pulito.
- Lint: **885 errori** (`prettier/prettier`) e 12 warning (`react-refresh/only-export-components`) su 58 file. Sono quasi tutti formattazione automatica, ma `bun run lint` oggi è rosso.
- Frontend: due rotte (`/`, `/dashboard`). Mancano ricerca e prenotazione cliente, check-in/check-out, manutenzioni, trasferimenti e gestione segnalazioni. `DOCUMENTAZIONE.md` §12 le elenca come da fare.
- Dati: l'istanza usa il seed (6 sedi, 48 veicoli, 12 clienti, 12 prenotazioni, 6 segnalazioni). L'import DAI funziona ma non è stato eseguito nell'istanza demo, e non c'è uno script che lo faccia.
- Amministrazione: nessun utente `cliente` nel seed, quindi l'area cliente non è dimostrabile nemmeno a mano.

### Documentazione e installazione (R5, R6)

- `DOCUMENTAZIONE.md`: buona copertura, ma tabella API da aggiornare (`/dashboard/flotta` cita solo operatore e admin, mancano `/dashboard/fermi` e `/veicoli/{id}/rientro-servizio`; il CEO è ammesso su più letture).
- `README.md`: numeri del seed sbagliati (riga 49); manca la procedura per importare i CSV DAI.
- `AGENTS.md` e `INTEGRAZIONE-FRONTEND-BACKEND.md`: descrivono il JWT in memoria e `src/lib/auth.ts`, che non esistono; la sessione è in `sessionStorage`.
- Installazione: `docker compose --env-file ../.env up --build` funziona, ma il servizio `api` parte con `--reload` (`docker-compose.yml:21`) e `ENVIRONMENT=development`.
- Nessuna CI (`.github/` contiene solo `copilot-instructions.md`), nessun deploy, nessun reverse proxy/HTTPS.

### GDPR (R8)

Implementato: cifratura a livello applicativo con `StringaCifrata` e blind index, diritti di accesso/portabilità/rettifica/cancellazione, consenso privacy, rotazione chiavi, log tecnici senza dati personali.

Da fare (da `DOCUMENTAZIONE.md` §8.4 e dal backlog): retention e cancellazione automatica, audit nominativo degli accessi, informativa privacy, registro dei trattamenti, procedura violazioni, NDA, pseudonimizzazione per DAI, cifratura di `Segnalazione.testo` e degli altri testi liberi.

### Scadenze (R9)

- SAL 1: 20/11/2026. Il repository non ha commit successivi al 19/11, quindi il congelamento non è ancora stato messo alla prova.
- Demo: 18/12/2026.
- Calendario DAI: 23–27/11 dizionario e primi KPI/previsione/classificatore; 30/11–04/12 versioni definitive; 07–11/12 integrazione.

## Priorità al 18/12

### P0 – bloccanti per una demo credibile

1. **KPI e previsione reali** oppure rimozione/etichettatura del grafico mock. Oggi la dashboard mostra dati inventati come se fossero previsioni.
2. **Classificazione dei messaggi** (anche un baseline TF-IDF) e import delle segnalazioni con categorie reali; nel frattempo non importare `segnalazioni.csv` vuoto.
3. **Dati DAI nell'istanza demo**: decidere le sedi (5 DAI o 6 app), importare veicoli e prenotazioni, documentare la procedura.
4. **Nomi delle sedi nel frontend** da `/dashboard/sedi`, non dalla mappa hardcoded; togliere “Milano” e “3 sedi”.
5. **Credenziali della demo**: impostare `CEO_PASSWORD`, cambiare admin/operatore, decidere se lasciare il pulsante demo.
6. **Area cliente e flussi operatore** se la demo deve mostrare “prenotare e gestire i noleggi”: oggi il backend c'è, l'interfaccia no.

### P1 – qualità e coerenza

7. CEO in sola lettura anche nell'interfaccia (niente select di modifica).
8. Allineare `README.md`, `DOCUMENTAZIONE.md` §9 e la documentazione della sessione al codice.
9. `eslint --fix` (885 errori di formattazione) e controllo in CI.
10. Togliere `--reload`, `ENVIRONMENT=development` e valutare HTTPS/reverse proxy per la demo.

### P2 – completamenti

11. Dizionario dei dati, report dei risultati, pseudonimizzazione, retention, audit accessi, informativa e registro dei trattamenti.
12. Copertura test su disponibilità e concorrenza; migrazioni Alembic.

## Cosa non ho verificato

- PostgreSQL reale per concorrenza e `SELECT … FOR UPDATE`.
- Invio effettivo delle email dal worker e resa in Mailpit.
- Supabase reale (JWKS, provisioning, refresh).
- Deploy e comportamento dietro HTTPS.
- Accessibilità e browser diversi da Chromium.
