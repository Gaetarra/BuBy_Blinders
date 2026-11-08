# Buby Rent Project Guidelines

## Build and run

The application is developed and run from [`buby-rent/`](../buby-rent/).
Docker and Docker Compose are the supported local prerequisites.

```bash
cd buby-rent
cp .env.example .env
# Set real values for POSTGRES_PASSWORD, SECRET_KEY, ENCRYPTION_KEYS,
# BLIND_INDEX_KEY, and the demo passwords in .env.
docker compose up --build
```

- API: `http://localhost:8000`; OpenAPI UI: `http://localhost:8000/docs`
- Frontend placeholder: `http://localhost:3000`
- Stop services: `docker compose down`
- Recreate the development database after schema/key changes:
  `docker compose down -v && docker compose up --build`
- Rotate encryption keys with:
  `docker compose exec api python -m app.rotate_keys`

There is currently no automated test suite, test runner, or lint configuration
in the repository. Do not invent a single-test command; add and document the
runner when tests are introduced.

See [`buby-rent/README.md`](../buby-rent/README.md) and
[`DOCUMENTAZIONE.md`](../DOCUMENTAZIONE.md) for the current setup, API examples,
GDPR checklist, and project status.

## Architecture

- [`buby-rent/docker-compose.yml`](../buby-rent/docker-compose.yml) runs three
  services: PostgreSQL 16 with the persistent `pgdata` volume, a FastAPI API,
  and an nginx container serving the current static frontend placeholder.
- The API lives in [`buby-rent/api/app/`](../buby-rent/api/app/). `main.py`
  creates the app, configures CORS, creates the current schema at startup, seeds
  mock data, and mounts the `auth`, `veicoli`, and `prenotazioni` routers.
- SQLAlchemy models and database sessions are in `models.py` and `database.py`.
  Pydantic request/response contracts are in `schemas.py`; configuration is read
  from environment variables in `config.py`.
- Availability queries are centralized in `availability.py`. A vehicle is
  unavailable for blocked states or overlapping active reservations. Reservation
  creation locks the vehicle row in the transaction before checking overlap.
- Authentication uses JWT access tokens and bcrypt password hashes. Request
  dependencies in `deps.py` load the user from the database on every request;
  authorization must use the database role, not the role claim alone.
- Personal names and emails use application-level Fernet encryption through
  `encrypted_types.py`. Exact email lookup and uniqueness use the HMAC blind
  index from `crypto.py`. Keep encryption keys outside the repository and
  preserve the documented key-rotation procedure.
- The frontend is intentionally only a static nginx placeholder; planned React,
  operator, maintenance, inspection, transfer, and DAI integration work is
  documented as unfinished in [`DOCUMENTAZIONE.md`](../DOCUMENTAZIONE.md).

## Repository-specific conventions

- Use the existing Italian domain vocabulary and state constants in `models.py`
  (`STATI_VEICOLO`, `STATI_PRENOTAZIONE`, role constants, and related blocked
  states) instead of duplicating string literals.
- Keep router handlers thin: obtain sessions with `get_db`, use shared
  dependencies for authentication/roles, and put availability rules in
  `availability.py`.
- Public vehicle search is unauthenticated. Reservation creation requires a
  logged-in user; clients can reserve only for themselves, while operators and
  admins may provide a `cliente_id`.
- Operators are restricted to vehicles belonging to their assigned `sede_id`;
  admins can manage all vehicles. Use `richiedi_ruoli(...)` for role-gated
  endpoints.
- New email fields that must support exact lookup should follow the existing
  encrypted-value plus `email_idx` pattern. Never log plaintext personal data or
  secrets.
- Development defaults and mock users are seeded at startup. Production must
  set real secrets: `main.py` rejects development keys when `ENVIRONMENT=production`.
- The current schema is created with `Base.metadata.create_all`; Alembic
  migrations are planned but not yet present. Schema changes in development
  require recreating the Compose volume as documented above.
- Update [`README.md`](../buby-rent/README.md) or
  [`DOCUMENTAZIONE.md`](../DOCUMENTAZIONE.md) when setup, API behavior, data
  protection, or project status changes.
