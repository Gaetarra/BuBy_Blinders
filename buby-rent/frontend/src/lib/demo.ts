import type { DashboardFlotta, FermoVeicolo, Utente, Veicolo } from "./api";

export const SEDI: Record<number, string> = { 1: "Torino Centro", 2: "Lago Maggiore · Stresa", 3: "Milano Porta Garibaldi" };

export const demoUser: Utente = { id: 1, email: "direzione@bubyrent.it", ruolo: "ceo", cliente_id: null, sede_id: null };

const veicoli: Veicolo[] = [
  { id: 1, sede_id: 1, tipo: "auto", targa: "AB123CD", stato: "noleggiato", km: 15000 },
  { id: 2, sede_id: 2, tipo: "ebike", targa: "EB001XX", stato: "danneggiato", km: 300 },
  { id: 3, sede_id: 2, tipo: "moto", targa: "MT777ZZ", stato: "disponibile", km: 100 },
  { id: 4, sede_id: 1, tipo: "furgone", targa: "FG452LM", stato: "in_manutenzione", km: 84210 },
  { id: 5, sede_id: 3, tipo: "auto", targa: "GH908PQ", stato: "disponibile", km: 22340 },
  { id: 6, sede_id: 3, tipo: "auto", targa: "GK115RT", stato: "prenotato", km: 9120 },
  { id: 7, sede_id: 1, tipo: "ebike", targa: "EB014TO", stato: "disponibile", km: 1240 },
  { id: 8, sede_id: 3, tipo: "furgone", targa: "FM330MI", stato: "noleggiato", km: 51200 },
  { id: 9, sede_id: 2, tipo: "auto", targa: "LS771ST", stato: "in_trasferimento", km: 30410 },
  { id: 10, sede_id: 1, tipo: "auto", targa: "TO562AA", stato: "noleggiato", km: 41870 },
  { id: 11, sede_id: 3, tipo: "ebike", targa: "EB022MI", stato: "disponibile", km: 860 },
  { id: 12, sede_id: 1, tipo: "moto", targa: "MT204TO", stato: "prenotato", km: 6400 },
];

const per: Record<string, number> = {};
veicoli.forEach((v) => (per[v.stato] = (per[v.stato] ?? 0) + 1));

export const demoFlotta: DashboardFlotta = {
  sede_id: null,
  veicoli_totali: veicoli.length,
  veicoli_per_stato: per,
  veicoli,
  prenotazioni: [
    { id: 101, veicolo_id: 1, cliente_id: 12, inizio: "2026-11-18T09:00:00", fine: "2026-11-21T18:00:00", stato: "in_corso" },
    { id: 102, veicolo_id: 6, cliente_id: 14, inizio: "2026-11-20T08:30:00", fine: "2026-11-22T19:00:00", stato: "confermata" },
    { id: 103, veicolo_id: 8, cliente_id: 21, inizio: "2026-11-17T10:00:00", fine: "2026-11-24T10:00:00", stato: "in_corso" },
    { id: 104, veicolo_id: 12, cliente_id: 9, inizio: "2026-11-21T09:00:00", fine: "2026-11-21T20:00:00", stato: "richiesta" },
    { id: 105, veicolo_id: 10, cliente_id: 33, inizio: "2026-11-15T09:00:00", fine: "2026-11-20T09:00:00", stato: "in_corso" },
    { id: 106, veicolo_id: 3, cliente_id: 12, inizio: "2026-11-10T09:00:00", fine: "2026-11-12T18:00:00", stato: "conclusa" },
    { id: 107, veicolo_id: 5, cliente_id: 40, inizio: "2026-11-25T09:00:00", fine: "2026-11-27T18:00:00", stato: "confermata" },
  ],
};

export const demoFermi: FermoVeicolo[] = [
  { veicolo: veicoli[1]!, priorita: 1, giorni_fermo: 8, motivo: "E-bike non si accende dopo la ricarica" },
  { veicolo: veicoli[3]!, priorita: 2, giorni_fermo: 5, motivo: "Tagliando programmato e sostituzione freni" },
  { veicolo: veicoli[8]!, priorita: 3, giorni_fermo: 2, motivo: "Trasferimento Stresa → Torino Centro" },
];

/** Weekly demand per site (demo forecast). */
export const demoDomanda = [
  { giorno: "Lun", torino: 14, stresa: 4, milano: 18 },
  { giorno: "Mar", torino: 12, stresa: 3, milano: 16 },
  { giorno: "Mer", torino: 15, stresa: 5, milano: 19 },
  { giorno: "Gio", torino: 17, stresa: 6, milano: 22 },
  { giorno: "Ven", torino: 21, stresa: 11, milano: 25 },
  { giorno: "Sab", torino: 19, stresa: 16, milano: 14 },
  { giorno: "Dom", torino: 11, stresa: 14, milano: 9 },
];
