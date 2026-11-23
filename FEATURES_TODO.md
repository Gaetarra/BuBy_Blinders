# Feature backlog – Buby Rent

## Panoramica
Di seguito sono elencate le funzionalità ancora da implementare nel progetto **Buby Rent** (secondo il backlog definito in `AGENTS.md`).  Per ciascuna feature è indicato lo **stato attuale**, le **mancanze** e i **passi consigliati** per completarla.

---

| # | Feature | Stato attuale | Cosa manca |
|---|---------|---------------|------------|
| **1** | **Gestione utenti da parte dell'admin** (creare operatori, cambiare ruoli) | Parzialmente implementata – l’admin dispone di utenti demo tramite lo *seed*, ma non c’è un endpoint UI/API per aggiungere/modificare operatori in runtime. | • Endpoint FastAPI `POST /admin/utenti`, `PUT /admin/utenti/{id}` con controlli di ruolo.<br>• UI admin per inserimento/modifica operatori.<br>• Test di permesso e integrazione. |
| **2** | **Includere manutenzioni e trasferimenti pianificati nel calcolo della disponibilità** | Disponibilità attuale gestita solo in `availability.py` sulle prenotazioni. | • Estendere la logica di disponibilità per considerare gli stati **`Manutenzione`** e **`Trasferimento`**.<br>• Aggiornare le query DB in `availability.py`.<br>• UI per visualizzare e inserire manutenzioni/trasferimenti.<br>• Test di conflitto (prenotazione vs manutenzione). |
| **3** | **Upload e conservazione sicura delle foto** (segnalazioni, ispezioni, manutenzioni) | Nessun meccanismo di upload; le foto sono solo riferimenti dummy. | • Integrare Supabase Storage (o bucket locale) per gestire upload con firma temporanea.<br>• Endpoint `POST /foto` con verifica permessi.<br>• Aggiornare componenti React per preview/upload.<br>• Test di sicurezza (autorizzazione, dimensioni, MIME). |
| **4** | **Import di previsioni/KPI del team DAI** (pseudonimizzazione) | I dati DAI sono importati, ma le previsioni/KPI non sono gestite. | • Definire schema `KPI` in SQLAlchemy.<br>• Creare script di import (simile a `import_dai.py`).<br>• Pseudonimizzare campi sensibili con `StringaCifrata`/`blind_index`.<br>• UI per visualizzare i KPI per sede. |
| **5** | **Migrazioni Alembic** (sostituire `Base.metadata.create_all()`) | Nessuna migrazione; schema ricreato al riavvio. | • Configurare Alembic (`alembic.ini`, env).<br>• Generare migrazioni per tutti i modelli esistenti.<br>• Aggiornare la procedura di avvio (`docker compose up`) per applicare migrazioni prima di `create_all`. |
| **6** | **Ampliare la copertura test** (unit e integrazione) | Test di base presenti; mancano test per i nuovi endpoint, permessi e logica di disponibilità avanzata. | • Scrivere test per le feature 1‑4 sopra.<br>• Aggiungere test di performance/concorrenza per `SELECT … FOR UPDATE`. |
| **7** | **Completare area cliente e flussi operatore nel frontend** | UI cliente parziale; mancano pagine di prenotazione, storico e gestione segnalazioni. | • Implementare rotte mancanti (`/clienti/...`).<br>• Collegare le API di prenotazione/segna­lazione.<br>• Test end‑to‑end (Vitest + Playwright). |
| **8** | **Retention, audit nominativo degli accessi, verifica email, lettore IMAP/provider** | Mailpit è usato solo per sviluppo; non c’è persistenza né audit. | • Integrare servizio reale per invio/verifica email (es. Mailgun, Gmail).<br>• Implementare audit log degli accessi (`AccessLog`).<br>• Aggiungere job di pulizia/retention dei dati. |

---

## Priorità consigliata (in ordine di implementazione)
1. **Gestione utenti admin** – fondamentale per consentire al responsabile di creare operatori senza ricostruire il DB.
2. **Disponibilità con manutenzioni/trasferimenti** – evita prenotazioni su veicoli non disponibili.
3. **Upload foto sicuro** – richiesto per le segnalazioni e le ispezioni.
4. **Migrazioni Alembic** – rende il database più robusto per modifiche future.
5. **Import KPI** – aggiunge valore analitico al prodotto.
6. **Ampliare copertura test** – garantisce stabilità delle nuove feature.
7. **Completare UI cliente** – migliora l’esperienza utente finale.
8. **Retention & audit** – requisiti di sicurezza e conformità a lungo termine.

---

## Come procedere
- **Apri una issue** per ciascuna voce (es. `feature/admin-user-management`).
- **Stabilisci uno sprint** di 2‑3 settimane per completare le prime tre priorità.
- **Aggiorna la documentazione** (`README.md`, `DOCUMENTAZIONE.md`) al termine di ogni feature.
- **Esegui la CI** (`docker compose exec api pytest`) per verificare che tutti i test passino.

---

*File generato automaticamente da Antigravity il 2026‑11‑23.*