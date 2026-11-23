# Rapporto – Buby Rent

Verifiche svolte il **23 novembre 2026** sullo stack in esecuzione (podman: `db`, `api`, `worker`, `frontend`, `mailpit`, `pgadmin`).

| Documento | Contenuto |
| --- | --- |
| [prove-accesso.md](./prove-accesso.md) | Accesso nel browser con i 6 operatori e il CEO, controlli di autorizzazione lato API, comportamenti di sessione, anomalie |
| [verifica-consegna.md](./verifica-consegna.md) | Confronto tra i requisiti della `Consegna progetto informazioni.md` e lo stato reale di WSA e DAI, con priorità al 18/12 |
| [screenshot/](./screenshot) | Schermate di login e dashboard per ogni account, errore password e modalità demo |

Note di lettura:

- Le password non sono riportate: sono lette da `../.env` (`OPERATORE_PASSWORD`) e, per il CEO, dal default di `config.py` perché `CEO_PASSWORD` non è impostata.
- Le prove sono state eseguite con Playwright (`playwright-core`) e il Chromium di sistema in headless, quindi su un browser reale ma non su Firefox, Safari o mobile.
- I dati sono quelli del seed presente nel database: l'import dei CSV del team DAI è stato verificato a parte su un database SQLite temporaneo, non nell'istanza demo.
