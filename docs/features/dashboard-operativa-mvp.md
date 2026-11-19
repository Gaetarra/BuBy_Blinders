# Dashboard operativa MVP

## Cosa fa

La dashboard organizza le attività operative in sezioni annidate sotto
`Dashboard`:

- Prenotazioni operative;
- Mezzi fermi e priorità;
- Manutenzioni;
- Trasferimenti.

Gli operatori lavorano solo sulla propria sede. Admin e CEO possono consultare
la flotta secondo i rispettivi permessi.

## Implementazione

- `GET /dashboard/flotta` aggrega veicoli e prenotazioni con filtro di sede.
- `GET /dashboard/fermi` calcola priorità e giorni di fermo.
- `POST /veicoli/{id}/rientro-servizio` rimette il mezzo in servizio e completa
  le manutenzioni attive.
- `operazioni.py` mantiene la logica di check-in, check-out, manutenzioni e
  trasferimenti.
- `dashboard.tsx` seleziona la sezione senza cambiare pagina e aggiorna le
  query dopo ogni operazione.

## Branch

`feature/dashboard-operativa-mvp`
