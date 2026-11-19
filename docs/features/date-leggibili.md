# Date leggibili

## Cosa fa

La UI e le email non mostrano più timestamp tecnici come
`2027-03-10T09:00:00`.

- dashboard: `10/03/2027 09:00`;
- email cliente: `10/03/2027 alle 09:00`;
- le API continuano a restituire ISO 8601 per interoperabilità.

## Implementazione

- `dashboard.tsx` centralizza la visualizzazione con `Intl.DateTimeFormat` e
  locale `it-IT`.
- `routers/prenotazioni.py` formatta le date prima di accodare il corpo email.
- I modelli e `api.ts` mantengono i valori datetime tecnici senza trasformarli
  nel layer dati.

## Branch

`feature/date-leggibili`
