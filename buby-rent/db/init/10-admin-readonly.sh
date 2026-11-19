#!/bin/sh
# Crea o aggiorna il ruolo PostgreSQL di sola lettura usato da pgAdmin.
# Viene eseguito a ogni `docker compose up` dal servizio db-admin-ro, quindi
# funziona anche su un volume pgdata gia inizializzato.
set -eu

: "${POSTGRES_USER:?POSTGRES_USER non impostato}"
: "${POSTGRES_DB:?POSTGRES_DB non impostato}"
: "${PGADMIN_RO_USER:?PGADMIN_RO_USER non impostato}"
: "${PGADMIN_RO_PASSWORD:?PGADMIN_RO_PASSWORD non impostato}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${PGADMIN_RO_USER}') THEN
    CREATE ROLE "${PGADMIN_RO_USER}" LOGIN PASSWORD '${PGADMIN_RO_PASSWORD}';
  ELSE
    ALTER ROLE "${PGADMIN_RO_USER}" WITH LOGIN PASSWORD '${PGADMIN_RO_PASSWORD}';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${PGADMIN_RO_USER}";
GRANT USAGE ON SCHEMA public TO "${PGADMIN_RO_USER}";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "${PGADMIN_RO_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "${PGADMIN_RO_USER}";
SQL

echo "Ruolo di sola lettura '${PGADMIN_RO_USER}' pronto."
