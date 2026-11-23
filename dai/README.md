# Buby Rent – Team DAI (Data Analyst e AI Specialist)

Progetto Laboratorio Integrato · ITS Academy ICT Piemonte · Caso 3: Trasporti con noleggi

Questa cartella contiene il lavoro del team DAI: dati, pulizia, analisi e componenti di intelligenza artificiale. L'applicazione web è del team WSA (`../buby-rent/`, documentata in `../DOCUMENTAZIONE.md`): i nostri risultati entrano nell'app attraverso il contratto dati.

## 1. Cosa dobbiamo consegnare

Dal documento del progetto (`../Consegna progetto informazioni.md`):

- dataset puliti e **dizionario dei dati**;
- notebook o script documentati;
- endpoint o file di output **nel formato concordato** con WSA (contratto dati);
- almeno una **componente di analisi** (i KPI del caso) e una **componente sui testi** (classificazione, estrazione di informazioni o sintesi); eventuale modello predittivo o componente basata su LLM, con un uso responsabile dell'AI;
- **report dei risultati** e demo finale.

Obiettivi del caso: prevedere la domanda per sede e periodo e migliorare l'utilizzo della flotta; classificare danni e richieste di assistenza e ridurre i tempi di fermo.

Valutazione DAI: correttezza e qualità dei dati, rigore dell'analisi, utilità e affidabilità delle componenti AI. Criteri comuni: qualità del prodotto, collaborazione tra i team, rispetto delle scadenze, chiarezza della documentazione, efficacia della demo.

## 2. Ruoli

Referente del team: **Gabriele**. La gerarchia è aperta: le decisioni si prendono insieme. Il referente tiene i contatti con WSA e con il cliente e manda lo stato settimanale.

Ruoli disponibili: ognuno sceglie quello più adatto a sé e scrive il proprio nome nella colonna «Chi». Un ruolo può avere più persone, e chi ha finito la propria parte aiuta gli altri.

| Ruolo | Di cosa si occupa | Consegne | Chi |
| --- | --- | --- | --- |
| Dati e integrazione | Pipeline di pulizia ed export per l'app, dettagli tecnici del contratto dati con WSA, pseudonimizzazione | Dataset puliti, dizionario dei dati, export per l'app | |
| Analisi e previsione | KPI della flotta (sezione 5) e previsione della domanda per sede e periodo | Notebook dei KPI, modello di previsione, file delle previsioni nel formato concordato | |
| Testi e AI | Classificazione dei messaggi dei clienti (categoria, urgenza, sintesi, targa citata) e sua valutazione | Notebook del classificatore, metriche sul test set, file delle classificazioni nel formato concordato | |
| Verifica a campione | Controlla un campione di righe pulite e di messaggi classificati, confrontandoli con l'originale, e annota gli errori trovati | Tabella delle verifiche, usata nel report come valutazione umana | Felipe |

Report dei risultati: ognuno scrive la sezione della propria parte; il referente la raccoglie in un unico documento.

## 3. Calendario

| Quando | Cosa |
| --- | --- |
| Gio 19/11 | Preparare il SAL 1: formati di scambio (sezione 6) e domande aperte per WSA |
| **Ven 20/11** | **SAL 1**: presentazione di analisi, schema dati e contratto; schema e contratto vengono congelati |
| 23–27/11 | Dizionario dei dati; KPI definiti e calcolati; prime versioni semplici di previsione e classificazione, con dati di test separati |
| 30/11–04/12 | Modello di previsione e classificatore definitivi, valutati; export di previsioni e classificazioni nel formato concordato (ultimo incontro in aula il 4/12) |
| 07–11/12 | Integrazione nell'app con WSA e prova dell'import; bozza del report dei risultati |
| 14–17/12 | Report finale, slide, prova della demo |
| **Ven 18/12** | **Presentazione finale** davanti al cliente |

Ogni settimana il referente manda al cliente un breve stato scritto (richiesto dal documento del progetto).

## 4. Dati e pipeline

Dati sintetici: nessuna persona o azienda reale. Periodo: 01/11/2025 – 10/11/2026. Sedi: `TOR` (Torino Lingotto), `ALB` (Alba), `BAR` (Bardonecchia), `STR` (Stresa), `CAS` (Casale Monferrato). Dettagli sui difetti presenti nei dati grezzi in `dati/README_dati_sporchi.md`.

```
files/                          anagrafiche: sedi, flotta (64 veicoli), tariffe
dati/buby_rent_dati_sporchi/    dati grezzi per sede: noleggi, manutenzioni, comunicazioni
dati/buby_rent_dati_sporchi/_ground_truth/   etichette corrette e log dei difetti: SOLO per valutare
dati/Notebooks_Buby_Rent/       notebook della pipeline
dati_puliti/                    output della pulizia (per sede e *_tutti_pulito.csv)
export_app/                     file pronti per l'importatore dell'app WSA
```

I notebook si eseguono dalla loro cartella, in quest'ordine: `01_data_noleggi` → `02_data_manutenzioni` e `03_data_comunicazioni` → `04_export_app`. Dipendenze in `dati/Notebooks_Buby_Rent/requirements.txt` (pandas, numpy).

```bash
cd dati/Notebooks_Buby_Rent
jupyter nbconvert --to notebook --execute --inplace 01_data_noleggi.ipynb
```

Volumi puliti: 4.997 noleggi, 861 interventi di manutenzione, 2.181 comunicazioni.

Le comunicazioni pulite **non hanno ancora etichette**: la classificazione è la componente AI ancora da fare (sezione 5). Il collegamento tra messaggi e noleggi (`id_noleggio_corretto`) concorda al 90,05% con il ground truth: alcune richieste di informazioni vengono collegate a un noleggio vicino. Quando ci sarà il classificatore, il notebook 03 potrà escluderle di nuovo (con le categorie si arrivava al 95%).

## 5. Analisi e AI

**KPI** (proposta, da rifinire):

- tasso di utilizzo della flotta: giorni noleggiati su giorni disponibili, per sede, tipo di veicolo e mese;
- giorni di fermo per manutenzioni e danni, per sede e tipo di intervento;
- costi di manutenzione per veicolo e per km;
- ricavi per sede e mese, ricavo medio per noleggio;
- tasso di annullamento e di no-show (colonna `no_show`);
- noleggi con riconsegna in un'altra sede: flussi tra sedi e sbilanciamento della flotta;
- valutazione media dei clienti;
- segnalazioni per categoria e urgenza (dopo la classificazione).

**Previsione della domanda**: numero di noleggi per sede, settimana e tipo di veicolo. Test sulle ultime settimane del periodo (split temporale), confronto con un modello di riferimento semplice (per esempio la media delle settimane precedenti), metriche MAE e MAPE. Attenzione: c'è un solo anno di dati, quindi la stagionalità annuale non si può stimare confrontando lo stesso periodo di anni diversi; servono caratteristiche di calendario (mese, festivi, fine settimana).

**Classificazione dei messaggi**: i campi da produrre si decidono al SAL 1 (sezione 6). Metodo:

1. divisione in addestramento e test, stratificata per categoria;
2. modello di riferimento semplice (TF-IDF e regressione logistica);
3. LLM a cui si passano come esempi i messaggi più simili presi dall'addestramento (approccio RAG);
4. confronto con accuratezza, F1 macro e matrice di confusione sul test. La sintesi si valuta a campione da una persona.

**Uso responsabile dell'AI**:

- `_ground_truth` serve solo a valutare: mai nella pulizia, mai come feature;
- il testo dei messaggi è un input non fidato: nessuna azione automatica nasce da quello che c'è scritto;
- prima di inviare testi a un servizio esterno si tolgono i dati personali;
- accesso e costi di un eventuale servizio LLM vanno concordati con il cliente.

## 6. Contratto dati con WSA

L'app importa CSV con `python -m app.import_csv` (`../buby-rent/api/app/import_csv.py`). Il notebook `04_export_app` produce in `export_app/` i tre file nel loro formato:

| File | Colonne | Righe |
| --- | --- | --- |
| `veicoli.csv` | `sede, citta, tipo, targa, stato, km` | 64 |
| `prenotazioni.csv` | `email_cliente, nome_cliente, targa, inizio, fine, stato` | 4.905 |
| `segnalazioni.csv` | `email_mittente, oggetto, testo, ricevuta_il, targa, categoria, urgenza, sintesi, targa_estratta` | 1.388 |

Verificati con l'importatore di WSA su un database di prova: tutte le righe importate, nessuna scartata.

- **Valori**: `tipo` usa i valori dell'app (`auto`, `furgone`, `ebike`), e `stato` delle prenotazioni gli stati dell'app (`conclusa`, `annullata`, `in_corso`).
- **No-show e targhe**: i no-show diventano `annullata`. Le e-bike usano il codice asset come targa.
- **Righe non esportate**: 88 noleggi con email del cliente non recuperabile e 4 con veicolo sconosciuto.
- **Segnalazioni**: `segnalazioni.csv` non va importato finché la classificazione non riempie `categoria`, altrimenti l'app assegna a tutte la categoria predefinita `guasto`.

**Domande aperte per il SAL 1**:

1. Campi della segnalazione: `AGENTS.md` cita `categoria`, `urgenza`, `sintesi` e `targa_estratta`, ma il modello dell'app oggi salva solo `categoria`. Quali campi tenere, e con quali valori ammessi? L'app usa categorie generali (`danno`, `guasto`...), i nostri dati ne hanno 16: serve una tabella di corrispondenza.
2. Quali messaggi diventano segnalazioni: solo danni e guasti, o tutti i messaggi dei clienti collegati a un veicolo? Le note di tecnici e operatori starebbero meglio nelle comunicazioni interne, che però non hanno un import.
3. Sedi della demo: confermate le 5 sedi dei dati DAI (Torino Lingotto, Alba, Bardonecchia, Stresa, Casale Monferrato), allineando anche il seed, i test e il frontend dell'app.
4. Formato di previsioni e KPI per gli endpoint previsti da WSA (`POST /import/previsioni`, `GET /previsioni/domanda`, `GET /kpi/utilizzo-flotta`): granularità, orizzonte e colonne.
5. Dati personali: i file per l'app contengono nomi ed email (fittizi), che l'app cifra. Nei dati che l'app passa a noi servono `cliente_id` al posto di nome ed email, e testi senza dati personali (`../DOCUMENTAZIONE.md`, sezione 8.4).

## 7. Regole di lavoro

- Lavoriamo solo in `dai/`. I file del team WSA (`../buby-rent/`, `../DOCUMENTAZIONE.md`, `../AGENTS.md`, `../docs/`, `../.github/`) non si modificano: se serve una modifica all'app, la si propone a WSA.
- Un branch per argomento (`dai/<argomento>`) e una pull request verso `main`, rivista da un altro membro DAI.
- Dopo ogni modifica a un notebook si rieseguono quelli che seguono, e si committano insieme notebook e CSV prodotti.
- Le metriche si calcolano solo su dati di test separati.
- Niente chiavi API o file `.env` nel repository.
- Quello che produce un assistente AI si controlla sempre prima del commit.

## 8. Stato

**Fatto**

- Dataset sintetico e pipeline di pulizia (notebook 01–03)
- Valori allineati all'app: tipo `ebike` e stati della prenotazione, con colonna `no_show`
- Export nei formati dell'importatore WSA (notebook 04), verificato con il loro importatore

**Da fare**

- [ ] SAL 1: presentare formati e domande aperte, congelare il contratto
- [ ] Dizionario dei dati
- [ ] KPI
- [ ] Previsione della domanda
- [ ] Classificazione dei messaggi e valutazione
- [ ] Filtro delle richieste di informazioni nel collegamento messaggi-noleggi (dopo la classificazione)
- [ ] Pseudonimizzazione dei dati scambiati con l'app
- [ ] Report dei risultati, slide e demo
