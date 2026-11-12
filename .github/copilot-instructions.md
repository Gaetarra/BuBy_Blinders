# Copilot instructions for Buby Rent

## Repository shape

This repo is the Buby Rent case study. The working app lives under `buby-rent/` and is intentionally simple:

- `buby-rent/docker-compose.yml`: Postgres 16, FastAPI, and the React frontend served by Nitro on Node.js.
- `buby-rent/api/app/main.py`: FastAPI app bootstrap, startup schema creation, mock data seeding, and router registration.
- `buby-rent/api/app/models.py`: SQLAlchemy tables and domain constants (`STATI_VEICOLO`, `STATI_PRENOTAZIONE`, roles, blocked states).
- `buby-rent/api/app/routers/`: `auth`, `veicoli`, and `prenotazioni` endpoint groups.
- `buby-rent/api/app/operazioni.py`: role-scoped fleet dashboard, inspections/check-in/check-out, reports, maintenance, and transfers.
- `buby-rent/api/app/availability.py`: centralized vehicle availability logic.
- `buby-rent/api/app/deps.py`: request-scoped auth and authorization checks.
- `buby-rent/api/app/crypto.py` and `encrypted_types.py`: data-protection and blind-index pattern for personal data.

The frontend in `buby-rent/frontend/src/` is the Lovable React/TanStack application. Its Docker image builds the Nitro `node-server` output and runs it with Node.js. The browser calls FastAPI via `VITE_API_URL` (local Compose default `http://localhost:8000`); keep the API CORS origin aligned with the frontend origin. Customer-facing flows remain incomplete.

## Build, run, and environment

Use Docker Compose from the project root as the default local workflow:

```bash
cd buby-rent
cp -n .env.example ../.env
# Fill in real values for POSTGRES_PASSWORD, SECRET_KEY, ENCRYPTION_KEYS,
# BLIND_INDEX_KEY, and demo passwords before starting the app.
docker compose --env-file ../.env up --build
```

Key commands:

```bash
cd buby-rent

docker compose --env-file ../.env down
# reset the DB volume if schema or keys changed

docker compose --env-file ../.env down -v && docker compose --env-file ../.env up --build

# rotate encryption keys after key changes

docker compose exec api python -m app.rotate_keys
```

Important runtime details:

- API: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- React frontend: http://localhost:3000
- The app creates tables on startup with `Base.metadata.create_all()` and seeds mocked data; Alembic migrations are not present yet.
- `ENVIRONMENT=production` will refuse to start if development secrets are still configured.
- API requests are written to `buby-rent/logs/api.log`; logs include request IDs and response metadata but not request bodies, auth headers, query strings, or exception messages.

## Tests and linting

The API tests use pytest with an isolated in-memory SQLite database. Run the suite and a focused test from `buby-rent/`:

```bash
docker build -f api/Dockerfile.test -t buby-rent-api-tests ./api
docker run --rm buby-rent-api-tests
docker run --rm buby-rent-api-tests python -m pytest -q tests/test_api.py::test_booking_overlap_returns_conflict
```

There is no lint configuration yet. The runtime image intentionally does not include test dependencies.

## High-level architecture

The app is a single FastAPI service backed by PostgreSQL. The big-picture flow is:

- `main.py` boots the app, configures CORS, validates dev secrets, creates schema, and loads mock data.
- `config.py` reads environment variables and exposes `settings` used throughout the app.
- SQLAlchemy models in `models.py` represent `Sede`, `Veicolo`, `Cliente`, `Prenotazione`, and `Utente`.
- `routers/auth.py` handles registration/login/profile/GDPR export and deletion flows.
- `routers/veicoli.py` exposes public availability search and role-gated vehicle state updates.
- `routers/prenotazioni.py` creates reservations and restricts visibility by user role and `cliente_id` ownership.
- `operazioni.py` serves the fleet dashboard and operator workflows; operators must be scoped to their assigned `sede_id`.
- `availability.py` is the central place for availability checks: blocked states and overlapping active reservations prevent a vehicle from being booked.
- Reservation creation locks the vehicle row inside the transaction before checking overlap so concurrent requests cannot double-book the same car.

The architecture intentionally keeps business logic close to the domain model and router handling thin. Keep it that way unless the task clearly requires broader changes.

## Project conventions that matter

- Use the repo's Italian domain vocabulary and the existing state constants from `models.py` instead of duplicating raw strings.
- Keep API handlers thin: use `get_db`, `utente_corrente`, and `richiedi_ruoli` rather than re-implementing auth logic in each route.
- Public vehicle search is unauthenticated; booking creation requires a logged-in user. Customers can reserve only for themselves; operators/admins may pass a `cliente_id` when allowed.
- Operators are limited to vehicles in their own `sede_id`; admins may manage all vehicles.
- The operator dashboard is `GET /dashboard/flotta`; vehicle and reservation filters must preserve the operator's server-side sede scope.
- Email fields should follow the existing encrypted-value + `email_idx` pattern (Fernet-encrypted value plus HMAC blind index).
- Do not log plaintext personal data, credentials, tokens, or secrets.
- Development defaults are intentionally insecure and are rejected in production. Keep real keys outside the repository in `.env` and back them up separately.
- When setup or API behavior changes, update `buby-rent/README.md` and/or `DOCUMENTAZIONE.md` in the same change.

## Data-protection requirements

Personal names and login emails are encrypted at the application layer. Exact lookup uses a separate HMAC blind index. Passwords are hashed with bcrypt. Treat this as a security-sensitive part of the codebase, not as a generic CRUD app.

The project also includes GDPR-focused endpoints:

- `GET /auth/me/dati` for export
- `PATCH /auth/me` for rectification
- `DELETE /auth/me` for deletion/anonimization

These flows should remain consistent with the privacy model described in `DOCUMENTAZIONE.md`.

## Working style for this repo

- Prefer surgical edits in the existing FastAPI + SQLAlchemy architecture.
- Maintain consent/privacy expectations when working with customer data.
- Keep new business rules in the shared domain/availability layer instead of scattering them through handlers.
- Match the current code style and Italian naming used by the project rather than introducing a different domain language.

## References

- `buby-rent/README.md`
- `DOCUMENTAZIONE.md`
- `buby-rent/.env.example`
- `buby-rent/api/app/main.py`
- `buby-rent/api/app/models.py`
- `buby-rent/api/app/availability.py`
- `buby-rent/api/app/deps.py`
