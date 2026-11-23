#!/usr/bin/env bash
set -euo pipefail

# Script per caricare i dati reali del team DAI (64 veicoli, 4.905 prenotazioni, 1.442 clienti)
# nell'applicazione Buby Rent, allineando le 5 sedi (Torino Lingotto, Alba, Bardonecchia, Stresa, Casale Monferrato).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/docker-compose.yml" ]]; then
    COMPOSE_DIR="$SCRIPT_DIR"
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    COMPOSE_DIR="$SCRIPT_DIR/buby-rent"
    REPO_ROOT="$SCRIPT_DIR"
fi

ENV_FILE="$REPO_ROOT/.env"

echo "=========================================================="
echo " Buby Rent - Procedura Caricamento Dati DAI"
echo "=========================================================="
echo "Cartella progetto: $COMPOSE_DIR"
echo "File ambiente:     $ENV_FILE"

# 1. Verifica file .env
if [[ ! -f "$ENV_FILE" ]]; then
    echo "==> File $ENV_FILE non trovato. Copio da .env.example..."
    cp -n "$COMPOSE_DIR/.env.example" "$ENV_FILE"
fi

# Assicura SEED_DATI_MOCK=false nel file .env
if grep -q "^SEED_DATI_MOCK=" "$ENV_FILE"; then
    sed -i 's/^SEED_DATI_MOCK=.*/SEED_DATI_MOCK=false/' "$ENV_FILE"
else
    echo "SEED_DATI_MOCK=false" >> "$ENV_FILE"
fi
echo "==> SEED_DATI_MOCK impostato su 'false' in $ENV_FILE"

# 2. Rileva comando Compose (docker compose o podman compose)
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    COMPOSE="docker compose --env-file $ENV_FILE"
elif command -v podman-compose &>/dev/null; then
    COMPOSE="podman-compose --env-file $ENV_FILE"
elif command -v podman &>/dev/null && podman compose version &>/dev/null; then
    COMPOSE="podman compose --env-file $ENV_FILE"
else
    echo "Errore: docker compose o podman-compose non trovato nel PATH." >&2
    exit 1
fi

cd "$COMPOSE_DIR"

# 3. Reset database
echo ""
echo "==> 1. Reset database (down -v per cancellare volumi e dati mock)..."
$COMPOSE down -v

# 4. Avvio container
echo ""
echo "==> 2. Avvio servizi (con le 5 sedi DAI e utenti demo, senza flotta mock)..."
$COMPOSE up -d --build

# 5. Attesa API pronta
echo ""
echo "==> 3. Attesa avvio API (/health)..."
PRONTO=0
for i in {1..30}; do
    if $COMPOSE exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" &>/dev/null; then
        echo "API pronta dopo circa $((i * 2)) secondi."
        PRONTO=1
        break
    fi
    sleep 2
done

if [[ "$PRONTO" -ne 1 ]]; then
    echo "Attenzione: l'API non ha risposto in tempo al controllo di salute." >&2
fi

# 6. Import dati DAI
echo ""
echo "==> 4. Importazione dataset DAI (/dai)..."
EXTRA_ARGS=""
if [[ "${1:-}" == "--segnalazioni" ]]; then
    EXTRA_ARGS="--segnalazioni"
    echo "Opzione: importazione segnalazioni inclusa."
fi

$COMPOSE exec -T api python -m app.import_dai /dai $EXTRA_ARGS

# 7. Verifica volumi nel DB
echo ""
echo "==> 5. Verifica volumi caricati nel database:"
$COMPOSE exec -T api python -c '
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Sede, Veicolo, Prenotazione, Cliente, Segnalazione

with SessionLocal() as db:
    sedi = db.scalar(select(func.count(Sede.id)))
    veicoli = db.scalar(select(func.count(Veicolo.id)))
    prenotazioni = db.scalar(select(func.count(Prenotazione.id)))
    clienti = db.scalar(select(func.count(Cliente.id)))
    segnalazioni = db.scalar(select(func.count(Segnalazione.id)))
    
    print(f"  • Sedi:         {sedi} (attese: 5)")
    print(f"  • Veicoli:      {veicoli} (attesi: 64)")
    print(f"  • Prenotazioni: {prenotazioni} (attese: 4905)")
    print(f"  • Clienti:      {clienti} (attesi: 1442)")
    print(f"  • Segnalazioni: {segnalazioni}")
'

echo ""
echo "=========================================================="
echo " Caricamento dati DAI completato con successo!"
echo "=========================================================="
echo "Accesso alla Dashboard: http://localhost:3000"
echo "Credenziali di accesso:"
echo "  • CEO (globale 5 sedi, sola lettura): buby@buby.it / buby12345"
echo "  • Admin (gestione 5 sedi):             admin@buby.it / admin12345"
echo "  • Operatore Torino Lingotto:           operatore.lingotto@buby.it / operatore12345"
echo "  • Operatore Alba:                      operatore.alba@buby.it / operatore12345"
echo "  • Operatore Bardonecchia:              operatore.bardonecchia@buby.it / operatore12345"
echo "  • Operatore Stresa:                    operatore.stresa@buby.it / operatore12345"
echo "  • Operatore Casale Monferrato:         operatore.casale-monferrato@buby.it / operatore12345"
echo "Documentazione API: http://localhost:8000/docs"
echo "=========================================================="
