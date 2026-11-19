# Comunicazioni interne

## Cosa fa

La dashboard offre una coda operativa per note interne:

- il testo è cifrato e non viene esposto all'area cliente;
- una nota può riferirsi a un veicolo o a una sede;
- admin e operatori possono creare comunicazioni;
- admin può assegnarle a un operatore;
- un operatore può prendere in carico una nota;
- l'operatore vede le comunicazioni della propria sede e quelle non smistate;
- CEO e admin possono consultare la vista globale.

## Implementazione

- `ComunicazioneInterna` usa `StringaCifrata` per il campo `testo`.
- Gli endpoint sono in `operazioni.py`:
  - `GET /dashboard/comunicazioni` (operatore, admin, CEO);
  - `POST /dashboard/comunicazioni` (operatore, admin);
  - `PATCH /dashboard/comunicazioni/{id}/assegnazione` (operatore, admin);
  - `GET /dashboard/operatori` (admin, CEO).
- Il filtro per sede viene applicato lato API con la condizione sede propria o
  sede nulla; un operatore senza sede riceve `403`.
- Il frontend implementa creazione, elenco e presa in carico nella sezione
  `Comunicazioni interne` di `dashboard.tsx`. Il selettore di assegnazione è
  visibile solo all'admin; il CEO vede la scheda in sola lettura.

## Branch

`feature/comunicazioni-interne`
