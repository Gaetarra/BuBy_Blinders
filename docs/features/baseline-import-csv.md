# Baseline e import CSV

## Cosa fa

La baseline aggiunta integra infrastruttura email, import iniziale dei dati e
configurazione runtime senza sostituire il frontend React esistente.

## Implementazione

- `import_csv.py` importa veicoli, prenotazioni e segnalazioni in modo
  rilanciabile tramite identificativi e controlli di duplicazione.
- Il compose monta la directory dati nel servizio API.
- Le configurazioni SMTP, Mailpit e polling sono esposte da `config.py` e
  `.env.example`.
- Il frontend già presente mantiene autenticazione, dashboard MVP, area CEO e
  flussi operativi.

## Branch

`feature/baseline-import-csv`
