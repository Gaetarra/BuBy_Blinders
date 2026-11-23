# Prove di accesso nel browser – operatori e CEO

**Data:** 23 novembre 2026
**Ambiente:** stack podman in esecuzione (frontend `http://localhost:3000`, API `http://localhost:8000`)
**Metodo:** Chromium 157 headless pilotato con Playwright (`playwright-core`), login dal form reale `POST /auth/login` → `/auth/me` → `/dashboard`. Per ogni account: nuova finestra isolata, compilazione di email e password, attesa del redirect, lettura di sidebar, KPI e tabella flotta, screenshot a pagina intera.

Credenziali lette da `../.env` (`OPERATORE_PASSWORD`) e, per il CEO, dal default di `config.py` (`CEO_PASSWORD` non è presente nel `.env`). Nessuna password compare in questo rapporto.

## Esito per account

Tutti gli account hanno effettuato il login e sono arrivati a `/dashboard` senza errori in console né richieste fallite.

| Account | Sede attesa | Login | Ruolo mostrato in sidebar | Veicoli | Fermi | Pren. attive | Esito |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `operatore@buby.it` | Torino Centro (id 7) | OK | Operatore · Sede 7 | 8 | 2 | 2 | OK con anomalia nome sede |
| `operatore.porta-susa@buby.it` | Porta Susa (8) | OK | Operatore · Sede 8 | 8 | 1 | 2 | OK con anomalia nome sede |
| `operatore.lingotto@buby.it` | Lingotto (9) | OK | Operatore · Sede 9 | 8 | 2 | 2 | OK con anomalia nome sede |
| `operatore.moncalieri@buby.it` | Moncalieri (10) | OK | Operatore · Sede 10 | 8 | 2 | 2 | OK con anomalia nome sede |
| `operatore.rivoli@buby.it` | Rivoli (11) | OK | Operatore · Sede 11 | 8 | 2 | 2 | OK con anomalia nome sede |
| `operatore.venaria-reale@buby.it` | Venaria Reale (12) | OK | Operatore · Sede 12 | 8 | 2 | 2 | OK con anomalia nome sede |
| `buby@buby.it` | tutte | OK | Direzione · Tutte le sedi | 48 | 11 | 12 | OK, ma controlli di modifica attivi |

Isolamento verificato: la tabella flotta di ogni operatore contiene solo le targhe della propria sede (`TO-701…`, `TO-801…`, `TO-901…`, ecc.) e la somma delle sei sedi è 48, pari alla vista del CEO.

## Autorizzazione lato API

| Verifica | Risultato |
| --- | --- |
| `/auth/me` restituisce ruolo e sede corretti per tutti e 7 gli account | OK |
| Operatore: `/dashboard/flotta` e `/dashboard/fermi` limitati alla propria sede | OK (8 veicoli, un solo `sede_id`) |
| Operatore: `?sede_id=` di un'altra sede | `403` “Puoi consultare solo la flotta della tua sede” |
| Operatore: `PATCH /veicoli/{id}/stato` su veicolo di altra sede | `403` “Puoi gestire solo i veicoli della tua sede” |
| Operatore: `GET /veicoli/49/segnalazioni` (altra sede) | `403` |
| Operatore: modifica di un veicolo della propria sede | `200` |
| CEO: vista globale | `200`, 48 veicoli su 6 sedi |
| CEO: `PATCH /veicoli/{id}/stato` | `403` “Permessi insufficienti” |
| CEO: `POST /dashboard/comunicazioni` | `403` |
| CEO: `POST /veicoli/{id}/rientro-servizio` | `403` |
| CEO: lettura comunicazioni e operatori | `200` |
| Admin senza `sede_id` | `422` “sede_id obbligatorio per admin” |
| Admin con `sede_id=7` | `200`, 8 veicoli |
| Senza token | `401` |
| Password errata | `401` “Email o password errate” |

La separazione dei ruoli è quindi corretta sul server; il problema è solo di interfaccia (vedi A4).

## Comportamenti di sessione e accesso

- **Password errata:** il form mostra `Email o password errate` e resta su `/`.
- **Deep link senza sessione:** `http://localhost:3000/dashboard` riporta a `/`.
- **Reload:** la sessione sopravvive al ricaricamento. Il token è in `sessionStorage` (`src/lib/session.ts:3-6`), quindi resiste al reload ma non alla chiusura della scheda. La documentazione dice il contrario (vedi A6).
- **Modalità demo:** il pulsante “Esplora con dati dimostrativi” entra in dashboard senza credenziali, con utente `direzione@bubyrent.it`, badge “Dati dimostrativi” e 12 veicoli mock.

## Anomalie trovate

### A1 – P1 – I nomi delle sedi non arrivano dal database
La sidebar e la colonna “Sede” mostrano `Sede 7 … Sede 12`, e il KPI dice “3 sedi” invece di 6. La mappa è scritta a mano in `buby-rent/frontend/src/lib/demo.ts:3` (`1: Torino Centro, 2: Lago Maggiore · Stresa, 3: Milano Porta Garibaldi`), mentre il database usa gli id 7–12. Esiste già `GET /dashboard/sedi` (`api/app/operazioni.py:65`) che il frontend non usa.
**Effetto in demo:** l'operatore non vede il nome della propria sede e compare “Milano”, che non esiste nel progetto.

### A2 – P1 – Il grafico “Domanda prevista per sede” è finto
`buby-rent/frontend/src/routes/dashboard.tsx:133` usa `demoDomanda` di `demo.ts:48` (serie Torino, Milano, Stresa), anche per gli account reali. Non è una previsione del team DAI né un dato dell'API.
**Effetto in demo:** si presenta come KPI una previsione inventata, con sedi inesistenti. Va sostituito, o etichettato esplicitamente come dimostrativo.

### A3 – P1 – Il CEO usa la password di default
`CEO_PASSWORD` non è nel `.env`, quindi vale `buby12345` (`api/app/config.py:41`, `docker-compose.yml:37`). Anche `ADMIN_PASSWORD` e `OPERATORE_PASSWORD` sono quelle di sviluppo: `DOCUMENTAZIONE.md` §15 chiede di cambiarle prima della demo.

### A4 – P2 – Il CEO vede i controlli di modifica
La tabella flotta mostra una select “Modifica” per ogni veicolo anche al CEO (`dashboard.tsx:117`), che il server rifiuta con `403`. La dashboard non nasconde i comandi in sola lettura previsti per il CEO.
**Effetto:** in demo si può cliccare e non succede nulla, senza messaggio d'errore visibile.

### A5 – P2 – Accesso demo senza autenticazione
Il pulsante “Esplora con dati dimostrativi” (`routes/index.tsx:113`) apre la dashboard reale con dati finti. Se la demo deve mostrare i permessi, va chiarito quando usarlo: non attraversa login, ruoli né dati veri.

### A6 – P3 – Documentazione della sessione non allineata
`AGENTS.md:105`, `buby-rent/INTEGRAZIONE-FRONTEND-BACKEND.md:13,77` e `frontend/AGENTS.md:34` dicono che il JWT sta “in memoria”, che si perde al reload e che vive in `src/lib/auth.ts`. Il codice usa `sessionStorage` in `src/lib/session.ts`; `src/lib/auth.ts` e `src/lib/mock.ts` non esistono (i mock sono in `demo.ts`).

### A7 – P3 – Copy della pagina di login
La pagina dichiara “3 Sedi attive”, mentre il seed ne crea 6. Coerente con A1, ma va corretto nello stesso intervento.

## Screenshot

In `rapporto/screenshot/`:

- `operatore-buby-it.png` (Torino Centro)
- `operatore-porta-susa-buby-it.png`
- `operatore-lingotto-buby-it.png`
- `operatore-moncalieri-buby-it.png`
- `operatore-rivoli-buby-it.png`
- `operatore-venaria-reale-buby-it.png`
- `buby-buby-it.png` (CEO)
- `login-password-errata.png`
- `demo-bypass.png`

## Cosa non è stato verificato

- Firefox, Safari, mobile e accessibilità con screen reader.
- Sessione Supabase (in questa istanza `SUPABASE_URL` non è impostata) e scadenza del token dopo 60 minuti.
- Scenari con il database importato dal team DAI: le prove usano il seed.
- Comportamento dietro HTTPS o reverse proxy.
