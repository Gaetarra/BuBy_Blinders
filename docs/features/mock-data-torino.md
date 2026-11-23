# Mock data Torino

## Cosa fa

Il dataset demo rappresenta una flotta variegata distribuita sulle 5 sedi dei
dati DAI (Torino Lingotto, Alba, Bardonecchia, Stresa, Casale Monferrato), con
auto, furgoni ed e-bike, prenotazioni, danni, manutenzioni, trasferimenti e
mezzi fermi.

## Implementazione

- `seed.py` crea sedi, utenti, clienti, veicoli e prenotazioni in modo
  rilanciabile. Con `SEED_DATI_MOCK=false` crea solo sedi e utenti.
- `import_dai.py` carica i CSV del team DAI sulle stesse sedi.
- Gli stati includono disponibilità, prenotazione, noleggio, manutenzione,
  danno e trasferimento.
- I record sono collegati alle sedi per alimentare dashboard e isolamento
  degli operatori.
- `Base.metadata.create_all()` crea le tabelle all'avvio; il seed completa
  solo i dati mancanti.

## Branch

`feature/mock-data-torino`
