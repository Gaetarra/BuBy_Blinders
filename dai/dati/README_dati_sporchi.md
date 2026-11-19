# Buby Rent – Dataset fittizio "sporco" (Caso 3, Laboratorio Integrato)

Tutti i dati sono **inventati**: nomi, e-mail (domini example.*), telefoni, P.IVA e testi non corrispondono a persone o aziende reali.
Base: `flotta_con_tariffe.csv`, `sedi.csv`, `tariffe.csv` (stessi id_veicolo, targhe, codici tariffa, cauzioni, km inclusi, coefficienti stagionali).
Periodo: 01/11/2025 – 10/11/2026 (alcuni noleggi risultano `in corso` alla data del 12/11/2026).

## Struttura
```
<SEDE>/strutturati/noleggi_<SEDE>.csv          contratti di noleggio (1 riga = 1 noleggio, con duplicati)
<SEDE>/strutturati/manutenzioni_<SEDE>.csv     interventi, fermi e costi di manutenzione
<SEDE>/non_strutturati/comunicazioni_<SEDE>.csv  email, WhatsApp/SMS, trascrizioni di chiamate, moduli web, note tecnici/operatori
_ground_truth/                                 SOLO per valutare i modelli (non darli in pasto alla pulizia)
   ground_truth_comunicazioni_<SEDE>.csv       categoria, componente, gravità, sentiment, fermo, lingua, id_noleggio corretto
   log_difetti_strutturati_<SEDE>.csv          difetti iniettati (id riga, campo, tipo)
```
Sedi: TOR, ALB, BAR, STR, CAS. CSV UTF-8, separatore `,`.

## Volumi
| Sede | Noleggi unici | Righe noleggi (con duplicati) | Interventi | Comunicazioni |
|---|---|---|---|---|
| TOR | 1731 | 1782 | 297 | 789 |
| ALB | 857 | 882 | 155 | 389 |
| BAR | 677 | 697 | 115 | 298 |
| STR | 921 | 948 | 156 | 391 |
| CAS | 811 | 834 | 138 | 354 |
| **Totale** | **4997** | 5143 | 861 | 2221 |

## Realismo incorporato
- Stagionalità diversa per sede (Bardonecchia: sci e estate MTB; Stresa: primavera-estate; Alba: autunno/tartufo; Torino e Casale più costanti, agosto basso).
- Noleggi non sovrapposti sullo stesso mezzo, km progressivi coerenti con `km_iniziali`, tariffe calcolate da `tariffe.csv` (mezza giornata, weekend, settimana, coefficienti alta/bassa stagione, extra km, penali di ritardo).
- Manutenzioni programmate (tagliandi, cambio gomme stagionale) e fermi dovuti a danni, guasti, forature, incidenti.
- Alcuni noleggi one-way (riconsegna in altra sede), annullamenti, no-show, ritardi, noleggi in corso.
- Comunicazioni collegate ai noleggi tramite `id_noleggio` (a volte mancante o errato, come nella realtà).

## Tipi di difetto iniettati (con conteggi totali nel log)
Date in formati misti (dd/mm/yyyy, ISO, dd/mm/yy, "12 mar 2026", mm/dd/yyyy ambiguo), id veicolo e targhe in varianti (minuscolo, senza trattino, id inesistente), nomi di sede/tipologie/stati/metodi di pagamento scritti in modi diversi, importi con "€", virgola/punto, "n.d."; valori mancanti o sentinella (`-`, `n.d.`, `0`), email/telefoni malformati, `km_fine` < `km_inizio` o con cifra in più, durate e totali incoerenti, importi x10 o negativi, valutazioni fuori scala, duplicati esatti e quasi-duplicati, righe fuori ordine.
Nei testi: refusi, maiuscole/minuscole casuali, accenti persi (`e'`), caratteri corrotti (`Ã¨`), `&nbsp;`, abbreviazioni da SMS, firme e footer, messaggi vuoti o "vedi allegato", alcune email in inglese/francese/tedesco, reinvii duplicati.

Conteggio difetti loggati: 21636
- valore_variante: 5608
- sede_nome_variante: 2736
- mancante: 2135
- canale_variante: 2052
- nominativo_variante: 1735
- formato_diverso: 1257
- formato_data_non_standard: 1208
- minuscolo: 827
- variante: 462
- maiuscolo: 385
- ragione_sociale_variante: 364
- dominio_errato: 266
- senza_trattino: 247
- senza_chiocciola: 191
- spazio_finale: 178
- variante_o_mancante: 166
- spazi: 153
- cifre_mancanti: 153
- formato_id: 152
- formato_data_americano_ambiguo: 149
- incoerente_con_date: 147
- spazio_al_posto_del_trattino: 138
- targa_al_posto_dell_id: 125
- mancante_con_noleggio_concluso: 111
- duplicato_esatto: 101
- zeri_iniziali_persi: 98
- totale_non_coerente_con_componenti: 97
- duplicato_con_formattazione_diversa: 65
- minore_di_km_inizio: 64
- trattini: 40
- comunicazione_duplicata_reinviata: 40
- valore_impossibile: 32
- id_veicolo_inesistente: 31
- anno_errato_riconsegna_prima_del_ritiro: 22
- fuori_scala: 22
- cifra_in_piu: 22
- testo_non_numerico: 22
- importo_x10: 20
- importo_negativo: 10
- negativo: 5

## Categorie delle comunicazioni (ground truth)
danno_carrozzeria, guasto_meccanico, guasto_elettrico_batteria, foratura, assistenza_stradale, incidente_sinistro, pulizia_igiene, ritardo_riconsegna, reclamo_addebito, richiesta_info, modifica_prenotazione, cancellazione, multa_ztl_pedaggio, oggetto_dimenticato, feedback_positivo, furto_smarrimento.
