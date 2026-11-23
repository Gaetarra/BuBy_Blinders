# Ruoli e sedi

## Cosa fa

Il sistema distingue cliente, operatore, admin e CEO:

- l'operatore gestisce solo la sede assegnata;
- l'admin gestisce tutte le sedi indicando l'ambito quando richiesto;
- il CEO vede i dati globali ma non esegue mutazioni;
- il cliente vede solo le proprie prenotazioni.

È disponibile almeno un operatore demo per ogni sede di Torino e dintorni.

## Implementazione

- `Utente.ruolo` e `Utente.sede_id` determinano l'autorizzazione.
- `richiedi_ruoli` protegge gli endpoint per ruolo.
- I controlli server-side verificano sempre la sede del veicolo o della
  prenotazione; il filtro frontend non è considerato una misura di sicurezza.
- Il seed crea gli account demo per Torino Lingotto, Alba, Bardonecchia,
  Stresa e Casale Monferrato (le sedi dei dati DAI).

## Branch

`feature/ruoli-e-sedi`
