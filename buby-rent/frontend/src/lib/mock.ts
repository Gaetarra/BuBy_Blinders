import type { Prenotazione, Utente, Veicolo } from "./api";

export const SEDI = [
  { id: 1, nome: "Torino Centro" },
  { id: 2, nome: "Lago Maggiore" },
];

const tipi = ["auto", "furgone", "ebike"];
const stati = [
  "disponibile",
  "disponibile",
  "noleggiato",
  "prenotato",
  "disponibile",
  "in_manutenzione",
  "noleggiato",
  "danneggiato",
  "in_trasferimento",
  "disponibile",
];

export const mockVeicoli: Veicolo[] = Array.from({ length: 36 }, (_, i) => ({
  id: i + 1,
  sede_id: (i % 2) + 1,
  tipo: tipi[i % 3 === 2 ? 2 : i % 5 === 0 ? 1 : 0]!,
  targa:
    i % 3 === 2
      ? `EB-${String(100 + i)}`
      : `G${String.fromCharCode(65 + (i % 26))}${300 + i * 7}${String.fromCharCode(70 + (i % 10))}${String.fromCharCode(75 + (i % 8))}`,
  stato: stati[(i * 7) % stati.length]!,
  km: i % 3 === 2 ? 800 + i * 40 : 12000 + i * 2350,
}));

const pStati = [
  "confermata",
  "in_corso",
  "conclusa",
  "richiesta",
  "annullata",
  "conclusa",
  "in_corso",
];
const base = new Date("2026-11-12T09:00:00Z").getTime();
export const mockPrenotazioni: Prenotazione[] = Array.from(
  { length: 24 },
  (_, i) => ({
    id: 240 - i,
    veicolo_id: ((i * 5) % 36) + 1,
    cliente_id: 10 + (i % 9),
    inizio: new Date(base + (i - 10) * 86400000).toISOString(),
    fine: new Date(base + (i - 7) * 86400000).toISOString(),
    stato: pStati[i % pStati.length]!,
  }),
);

export const mockMe: Utente = {
  id: 1,
  email: "admin@buby.it (demo)",
  ruolo: "admin",
  cliente_id: null,
  sede_id: null,
};
