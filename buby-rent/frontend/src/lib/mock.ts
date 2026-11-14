import type { Prenotazione, Utente, Veicolo } from "./api";

export const SEDI = [
  { id: 1, nome: "Torino Centro" },
  { id: 2, nome: "Porta Susa" },
  { id: 3, nome: "Lingotto" },
  { id: 4, nome: "Moncalieri" },
  { id: 5, nome: "Rivoli" },
  { id: 6, nome: "Venaria Reale" },
];

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
const flotta = [
  ["auto", "Fiat 500", "TO"],
  ["auto", "Toyota Yaris", "TO"],
  ["furgone", "Fiat Ducato", "TO"],
  ["ebike", "E-bike Trek", "EB"],
  ["auto", "Jeep Renegade", "TO"],
  ["ebike", "E-bike Bianchi", "EB"],
  ["auto", "Renault Clio", "TO"],
  ["furgone", "Ford Transit", "TO"],
];

export const mockVeicoli: Veicolo[] = Array.from({ length: 48 }, (_, i) => ({
  id: i + 1,
  sede_id: (i % SEDI.length) + 1,
  tipo: flotta[i % flotta.length]![0],
  targa: `${flotta[i % flotta.length]![2]}-${String(100 + i).padStart(3, "0")}`,
  stato: stati[(i * 7) % stati.length]!,
  km:
    flotta[i % flotta.length]![0] === "ebike" ? 800 + i * 140 : 9000 + i * 1875,
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
  { length: 36 },
  (_, i) => ({
    id: 360 - i,
    veicolo_id: ((i * 5) % mockVeicoli.length) + 1,
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
