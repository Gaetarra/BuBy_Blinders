# Mock data Torino

## Cosa fa

Il dataset demo rappresenta una flotta variegata distribuita nelle zone di
Torino e dintorni, con auto, furgoni ed e-bike, prenotazioni, danni,
manutenzioni, trasferimenti e mezzi fermi.

## Implementazione

- `seed.py` crea sedi, utenti, clienti, veicoli e prenotazioni in modo
  rilanciabile.
- Gli stati includono disponibilità, prenotazione, noleggio, manutenzione,
  danno e trasferimento.
- I record sono collegati alle sedi per alimentare dashboard e isolamento
  degli operatori.
- `Base.metadata.create_all()` crea le tabelle all'avvio; il seed completa
  solo i dati mancanti.

## Branch

`feature/mock-data-torino`
