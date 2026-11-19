# ISTITUTO TECNOLOGICO SUPERIORE ACADEMY PER LE TECNOLOGIE DELLA INFORMAZIONE E DELLA COMUNICAZIONE DEL PIEMONTE
**Sede legale:** Torino, Piazza Carlo Felice 18

---

**Oggetto:** PROGETTO LABORATORIO INTEGRATO  
**PERCORSI FORMATIVI:** Data Analyst e Ai Specialist – Web Solutions Architect

---

## DESCRIZIONE COMMESSA

Buby Group è una holding che investe in quattro settori: turismo, rete solidale, trasporti con noleggi e sostenibilità. Ogni settore è rappresentato da una società controllata, che costituisce un caso del laboratorio: **Buby Travel, Buby Solidale, Buby Rent** e **Buby Green**.

Per ciascun caso Buby Group mette a disposizione dati strutturati (file Excel, tabelle) e non strutturati (email, messaggi, testi, documenti) e richiede di trasformarli in informazioni utilizzabili, rese accessibili ai propri utenti attraverso un’applicazione web. Gli studenti di Data Analyst e AI Specialist si occupano dei dati e delle componenti di intelligenza artificiale; gli studenti di Web Solutions Architect progettano e realizzano backend e frontend dell’applicazione.

Il laboratorio simula un vero progetto con cliente: due team con competenze diverse devono accordarsi su un contratto dati, rispettare le scadenze e consegnare un prodotto funzionante.

### *Casi proposti*

**Caso 1 – Turismo: Buby Travel.** Gestisce hotel e strutture ricettive sul lago e in montagna, con vendita diretta e tramite portali di prenotazione. Occupazione e prezzi sono gestiti con poca analisi dei dati; recensioni e richieste degli ospiti non vengono analizzate in modo sistematico.
- Individuare i fattori che influenzano soddisfazione e reputazione degli ospiti.
- Prevedere la domanda e supportare le decisioni sui prezzi.
- Dare alla direzione una dashboard su occupazione e reputazione, con un assistente che aiuta a rispondere alle richieste.

**Caso 2 – Rete solidale: Buby Solidale.** Raccoglie eccedenze alimentari e beni di prima necessità da aziende e donatori e li distribuisce ai punti di ritiro, con il supporto di volontari. Donazioni, giacenze, distribuzioni e turni sono sparsi in file diversi e in messaggi liberi: sprechi, squilibri tra punti di ritiro e difficoltà nell’organizzare i volontari.
- Prevedere fabbisogni ed eccedenze per ridurre gli sprechi.
- Rendere semplice per donatori e volontari inserire donazioni e gestire i turni.
- Misurare l’impatto sociale con indicatori chiari (pasti distribuiti, kg recuperati).

**Caso 3 – Trasporti con noleggi: Buby Rent.** Noleggia auto, furgoni ed e-bike a privati e aziende, con più sedi sul territorio. La flotta non è sempre distribuita dove serve, i veicoli restano fermi a lungo per manutenzioni e danni, e le segnalazioni di clienti e tecnici arrivano in forma libera e disordinata.
- Prevedere la domanda per sede e periodo e migliorare l’utilizzo della flotta.
- Classificare danni e richieste di assistenza e ridurre i tempi di fermo.
- Offrire un’applicazione per prenotare e gestire i noleggi, con un’area operatore per flotta e manutenzioni.

**Caso 4 – Sostenibilità: Buby Green.** Gestisce impianti fotovoltaici condivisi e distribuisce l’energia prodotta ai soci (famiglie, imprese, enti). Produzione e consumi non sono monitorati in modo integrato, l’impatto ambientale non è misurato in modo chiaro e le segnalazioni dei soci non vengono analizzate.
- Prevedere produzione e consumi e individuare anomalie negli impianti.
- Calcolare e rendere visibile l’impatto ambientale (CO2 evitata, risparmi).
- Coinvolgere i soci con un portale che mostra consumi e impatto, un simulatore di risparmio e la gestione delle segnalazioni.

I quattro casi possono essere assegnati a team diversi che, a fine percorso, possono integrare i propri risultati in un cruscotto di gruppo con indicatori condivisi (ricavi, impatto sociale e ambientale, soddisfazione dei clienti). Il caso 2 tratta dati su persone in situazione di fragilità: anche se fittizi, è un’occasione per lavorare su anonimizzazione e uso etico dei dati.

### *Dati di partenza per ciascun caso*

| Caso | Dati strutturati | Dati non strutturati |
| :--- | :--- | :--- |
| **Buby Travel** | Prenotazioni, occupazione, tariffe, stagionalità, canali di vendita | Recensioni online, email di richiesta informazioni, messaggi e reclami degli ospiti |
| **Buby Solidale** | Donazioni, giacenze, distribuzioni per punto di ritiro, turni dei volontari, dati anonimi sui beneficiari | Email di donatori e partner, messaggi dei volontari, note degli operatori sociali |
| **Buby Rent** | Contratti di noleggio, disponibilità dei veicoli, chilometraggi, costi di manutenzione, tariffe | Email dei clienti, descrizioni dei danni, note dei tecnici, richieste di assistenza |
| **Buby Green** | Produzione fotovoltaica, consumi dei soci, bollette, stime delle emissioni evitate | Email e segnalazioni dei soci, verbali delle assemblee, comunicazioni sui guasti degli impianti |

---

## OBIETTIVO TECNICO DA RAGGIUNGERE

Al termine del laboratorio ogni team deve consegnare, come risultato minimo, un prodotto funzionante e integrato:
- dati strutturati e non strutturati puliti, documentati e resi disponibili nel formato concordato (contratto dati: schema, formato dell’API, esempi di risposta);
- almeno una componente di analisi (KPI richiesti dal caso) e una componente di elaborazione di testi/email (classificazione, estrazione di informazioni o sintesi);
- un’applicazione web funzionante, con database, API e interfaccia (dashboard, ricerca, visualizzazioni), che utilizza i dati reali preparati dal team dati;
- documentazione tecnica, repository del codice, istruzioni di installazione e demo finale davanti all’azienda.

Organizzazione: team misti di 5–6 persone (ad esempio 2–3 studenti Data Analyst e AI Specialist e 2–3 studenti WSA), che lavorano sullo stesso caso o su casi differenti; in alternativa, una sola squadra per corso che collabora a livello di classe. Il **contratto dati** viene definito nella seconda settimana: da quel momento i WSA sviluppano con dati di prova (mock), mentre i Data Analyst preparano i dati reali; l’integrazione avviene nelle settimane finali.

---

## DESCRIZIONE DELLE ATTIVITÀ SPECIFICHE PER OGNI CORSO

### Data Analyst e Ai Specialist
- Esplorazione, pulizia e normalizzazione dei dati strutturati.
- Elaborazione dei dati non strutturati (email e testi): classificazione, estrazione di informazioni, sintesi.
- Analisi e definizione dei KPI richiesti dall’azienda.
- Eventuale modello predittivo o componente basata su LLM; uso responsabile dell’AI.
- **Consegne:** dataset puliti, data dictionary, notebook o script documentati, endpoint o file di output nel formato concordato, report dei risultati.

### Web Solution Architect
- Analisi dei requisiti e progettazione dell’architettura.
- Backend: database, API, autenticazione, gestione dei dati ricevuti dal team dati.
- Frontend: dashboard, ricerca, visualizzazioni, esperienza d’uso.
- Integrazione, test e rilascio dell’applicazione.
- **Consegne:** applicazione funzionante, documentazione tecnica (architettura, API), repository del codice, istruzioni di installazione.

---

## TECNOLOGIE, SOFTWARE E STRUMENTI DA UTILIZZARE

### Data Analyst e Ai Specialist
- Strumenti per l’esplorazione e la pulizia dei dati (Excel, Python/notebook o strumenti equivalenti), data dictionary.
- Tecniche di NLP e/o servizi AI per classificazione, sintesi ed estrazione di entità da testi ed email.
- Strumenti di analisi e visualizzazione per i KPI; eventuali modelli predittivi.

### Web Solution Architect
- Ambienti di sviluppo, database, API e framework per backend e frontend.
- Repository condiviso per il codice e la documentazione; spazio per il deploy.
- Integrazione di servizi esterni, test e rilascio.

**Requisiti da definire con l’azienda:** anonimizzazione dei dati, accordo di riservatezza (NDA) e rispetto del GDPR, in particolare per le email; dati disponibili entro la prima settimana; presenza dell’azienda al kick-off e alla demo finale ed eventuale referente per domande; accesso a eventuali servizi AI e relativi costi; proprietà di codice, analisi e modelli prodotti.

---

## Calendario

Otto incontri in aula dal 16 ottobre al 4 dicembre 2026, orario 14–18 indicativo. Il cliente è presente quattro volte. Qui le date più importanti:
- **Lun 26 ott** – kickoff: presentazione dell’azienda, del progetto, intervista raccolta requisiti, formazione dei team (cliente presente);
- **Ven 20 nov** – <mark>SAL 1: presentazione di analisi, processo, schema dati e contratto API; schema e contratto vengono congelati (cliente presente);</mark>
- **Ven 18 dic** – presentazione finale dei progetti (cliente presente).

I team leader tengono aggiornato il cliente con un breve stato scritto ogni settimana tramite l’indirizzo drive.

---

## CRITERI DI VALUTAZIONE

La valutazione combina criteri comuni e criteri specifici per corso.
- **Comuni:** qualità del prodotto finale, collaborazione tra i team, rispetto delle scadenze, chiarezza della documentazione, efficacia della demo.
- **Data Analyst e Ai Specialist:** correttezza e qualità dei dati, rigore dell’analisi, utilità e affidabilità delle componenti AI.
- **Web Solution Architect:** qualità dell’architettura e del codice, funzionamento e usabilità dell’applicazione, integrazione con i dati reali.

---

*Rev. 09 del 15/07/2026 — Intervento realizzato da ITS Academy ICT Piemonte*