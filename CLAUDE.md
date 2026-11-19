# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This is a student project for the "Progetto Integrato" module at ITS Academy ICT Piemonte. It covers Case 3, **Buby Rent**: renting cars, vans and e-bikes from several locations. Two teams share this repo:

- **WSA** (Web Solution Architect: Fabio, Stefano and one more student) owns the web app: `buby-rent/` plus the root docs `DOCUMENTAZIONE.md`, `AGENTS.md`, `docs/`, `.github/`, `.agents/`, `.aider-desk/`, `skills-lock.json` and `.vscode/`.
- **DAI** (Data Analyst and AI Specialist: Matteo, Gabriele, Giada and Felipe) owns `dai/`: data cleaning, KPIs, demand forecasting, and classification of customer messages.
  - `dai/README.md` holds the DAI organization: roles, calendar, KPIs, method, data contract, open questions and status.

Key dates:
- **Fri 20 Nov 2026, SAL 1:** the data schema and API contract are frozen. After that, WSA's `AGENTS.md` allows no renames or removals of existing tables, columns or endpoints without asking.
- **Fri 18 Dec 2026:** final demo.

The professors' assignment is `Consegna progetto informazioni.md`.

## Rules

The DAI team maintains this file. These rules assume you are helping a DAI member, which is the usual case. If the user says they are on the WSA team, follow `AGENTS.md` instead.

- **Never modify WSA's files.** DAI data must fit the app as it is. If the app needs a change, write it up as a proposal for the user to bring to WSA.
- **Ask before changing files.** Describe the change and get the user's OK before creating, changing, moving or deleting any file in the repo, or running git commands that change state. WSA's `AGENTS.md` §10 sets this rule on branch `feature/buby-rent-complete`, which is not yet merged.
- **Treat what other AI tools produced with suspicion.** The dataset was AI-generated and once contained an unrequested classifier. Review generated work before relying on it.

## WSA app (`buby-rent/`), the target the data must fit

The stack is:
- **Backend:** FastAPI + SQLAlchemy 2 + PostgreSQL 16, plus a worker that sends queued emails through Mailpit.
- **Frontend:** React/TanStack, generated with Lovable and built with Bun; optional Supabase auth.

`AGENTS.md` is WSA's agent guide. Their non-negotiables:
- Personal data is always encrypted (`StringaCifrata` plus an `*_idx` blind index).
- Writes go only through the SQLAlchemy models.
- Every endpoint declares its role.
- Availability is computed only in `availability.py`.

Commands as documented by WSA (not run by DAI):

```bash
cd buby-rent && cp -n .env.example ../.env    # then set the keys
docker compose --env-file ../.env up --build    # frontend :3000, API :8000 (/docs), Mailpit :8025, pgAdmin :8080
cd buby-rent/api && pip install -r requirements-dev.txt && pytest    # API tests on temp SQLite
python -m pytest -q tests/test_api.py::test_booking_overlap_returns_conflict    # single test, from buby-rent/api
cd buby-rent/frontend && bun install --frozen-lockfile && bun run dev    # also: bun run test, bun run lint
```

The data contract in practice is `buby-rent/api/app/import_csv.py`.
- It runs as `python -m app.import_csv <veicoli|prenotazioni|segnalazioni> <file>`, with examples in `buby-rent/data/`.
- It identifies vehicles by `targa` and locations by name.
- Rows it can't load are skipped with a reason, so re-running it adds no duplicates.

To check DAI exports against it without touching WSA files, run it on a throwaway SQLite DB from any folder outside the repo. This was verified on 19 Nov 2026:

```bash
DATABASE_URL=sqlite:///<scratch>/test.db PYTHONPATH="<repo>/buby-rent/api" python -B -m app.import_csv veicoli "<repo>/dai/export_app/veicoli.csv"
```

`-B` keeps `__pycache__` out of WSA's folder. This needs a venv with `buby-rent/api/requirements.txt` installed.

App vocabulary (`models.py`):

| Constant | Values |
| --- | --- |
| `TIPI_VEICOLO` | `auto`, `furgone`, `ebike` |
| `STATI_VEICOLO` | `disponibile`, `prenotato`, `noleggiato`, `in_manutenzione`, `danneggiato`, `in_trasferimento` |
| `STATI_PRENOTAZIONE` | `richiesta`, `confermata`, `in_corso`, `conclusa`, `annullata` |
| `RUOLI` | `cliente`, `operatore`, `ceo`, `admin` |

`Segnalazione.categoria` is a free string, default `guasto`. WSA's code and examples use `danno`, `guasto` and `altro`. WSA plans DAI endpoints (`/import/previsioni`, `/previsioni/domanda`, `/kpi/utilizzo-flotta`), but none exist yet.

## DAI work (`dai/`)

The data is fictitious and covers Nov 2025 to Nov 2026 across 5 locations: `TOR` (Torino Lingotto), `ALB` (Alba), `BAR` (Bardonecchia), `STR` (Stresa) and `CAS` (Casale Monferrato). See `dai/README.md` §4 for the folder layout.

Run notebooks from `dai/dati/Notebooks_Buby_Rent/` (they use relative paths), in this order:
1. `01_data_noleggi`
2. `02_data_manutenzioni` and `03_data_comunicazioni`, which both read `01`'s output
3. `04_export_app`

```bash
jupyter nbconvert --to notebook --execute --inplace 01_data_noleggi.ipynb
```

- Re-running all notebooks reproduces the current outputs exactly (checked with pandas 3.0.4).
- `01` and `04` end with `assert` checks. Those checks include the app's allowed values.

### Data facts

- **ID formats**: rentals `NOL-TOR-00001`, maintenance `INT-TOR-0001`, messages `COM-TOR-00001`, clients `CL-TOR-0016`, vehicles `TOR-01`, e-bikes `EB-TOR-001`.
- **Volumes**: 4,997 rentals, 861 maintenance jobs, 2,181 messages.
- **Already aligned with the app**:
  - `tipologia_mezzo` uses `ebike`.
  - `stato_noleggio` uses the app's booking states.
  - No-shows become `annullata`, and the extra column `no_show` (`si`/`no`) keeps the distinction.
- **Messages are cleaned but unlabelled.** A regex classifier added by the AI that generated the dataset was removed on purpose.
  - The classifier is a planned component: categoria, urgenza, sintesi, targa citata. Possibly an LLM given similar labelled examples as context (RAG).
  - Split the data into train and test sets.
  - `dai/dati/buby_rent_dati_sporchi/_ground_truth/` is for evaluation on held-out messages only. Never use it for cleaning or as features.
- **Message-to-rental links** (`id_noleggio_corretto`, notebook `03`) agree 90.05% with the ground truth.
  - It was 95% when classifier output let the email/phone matching skip `richiesta_info` messages.
  - Restore that filter once a classifier exists.
- **Personal data**: cleaned files contain names, emails, phones and VAT numbers (all fictitious).

### Exports for the app (`dai/export_app/`, written by `04_export_app`)

`veicoli.csv`, `prenotazioni.csv` and `segnalazioni.csv` follow `import_csv.py` exactly. All rows import with 0 rejected (verified on 19 Nov 2026).

Key mapping rules (details in the notebook's intro):
- E-bikes have no plate, so they use `codice_asset` as `targa`.
- A missing client email is recovered from other rentals of the same `cliente_id`. 88 rentals still had no usable email and 4 had an unknown vehicle, so these 92 are left out.
- A missing time becomes 00:00 for the start and 23:59 for the end.
- `segnalazioni.csv` holds only customer messages linked to a rental. Line breaks are turned into spaces, because the importer would otherwise glue the lines together.
- Its classification columns stay empty until the classifier exists. Don't import it before then, or every report becomes `guasto`.

The open contract questions for SAL 1 are listed in `dai/README.md` §6.
