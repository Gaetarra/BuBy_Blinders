import { getSession, logout } from "./auth";
import { mockPrenotazioni, mockVeicoli, mockMe } from "./mock";
import {
  isSupabaseConfigurationIncomplete,
  isSupabaseConfigured,
  supabase,
} from "./supabase";

export const API_URL =
  import.meta.env["VITE_API_URL"]?.trim() || "http://localhost:8000";

export type Veicolo = {
  id: number;
  sede_id: number;
  tipo: string;
  targa: string;
  stato: string;
  km: number;
};
export type Prenotazione = {
  id: number;
  veicolo_id: number;
  cliente_id: number;
  inizio: string;
  fine: string;
  stato: string;
};
export type Utente = {
  id: number;
  email: string;
  ruolo: string;
  cliente_id: number | null;
  sede_id: number | null;
};
export type DashboardFlotta = {
  sede_id: number | null;
  veicoli_totali: number;
  veicoli_per_stato: Record<string, number>;
  veicoli: Veicolo[];
  prenotazioni: Prenotazione[];
};
export type ClienteRiferimento = { id: number };
export type IspezioneInput = {
  km?: number;
  carburante?: number | null;
  batteria?: number | null;
  foto_url?: string | null;
  note?: string | null;
  danni_rilevati?: boolean;
};
export type FermoVeicolo = {
  veicolo: Veicolo;
  priorita: number;
  giorni_fermo: number;
  motivo: string;
};
export type ComunicazioneInterna = {
  id: number;
  sede_id: number | null;
  veicolo_id: number | null;
  testo: string;
  stato: string;
  creato_da_id: number;
  assegnato_a_id: number | null;
  creato_il: string;
};
export type Operatore = { id: number; email: string; sede_id: number | null };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  tokenOverride?: string,
): Promise<T> {
  const session = getSession();
  const headers = new Headers(init.headers);
  const token = tokenOverride ?? session?.token;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Impossibile raggiungere l'API su ${API_URL}`);
  }

  if (response.status === 401 && session) {
    void logout()?.catch((error: unknown) => {
      console.error(
        "Logout Supabase non riuscito:",
        error instanceof Error ? error.message : "errore non specificato",
      );
    });
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      typeof body.detail === "string"
        ? body.detail
        : `Errore ${response.status}`,
    );
  }
  return response.json();
}

export async function login(email: string, password: string): Promise<string> {
  if (isSupabaseConfigurationIncomplete) {
    throw new ApiError(
      0,
      "Configurazione Supabase incompleta: servono URL e chiave publishable.",
    );
  }

  if (isSupabaseConfigured) {
    if (!supabase) throw new ApiError(0, "Client Supabase non disponibile.");
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw new ApiError(error.status ?? 401, error.message);
    if (!data.session)
      throw new ApiError(
        401,
        "Supabase non ha restituito una sessione valida.",
      );

    try {
      await request<Utente>(
        "/auth/supabase/provision",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
        data.session.access_token,
      );
    } catch (provisionError) {
      await supabase.auth.signOut();
      throw provisionError;
    }
    return data.session.access_token;
  }

  const body = new URLSearchParams({ username: email, password });
  const response = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  return response.access_token;
}

const demo = () => getSession()?.demo === true;

export const getMe = () =>
  demo() ? Promise.resolve(mockMe) : request<Utente>("/auth/me");
export const getComunicazioniInterne = () =>
  request<ComunicazioneInterna[]>("/dashboard/comunicazioni");
export const getOperatori = () => request<Operatore[]>("/dashboard/operatori");
export const creaComunicazioneInterna = (input: {
  testo: string;
  sede_id?: number;
  veicolo_id?: number;
  assegnato_a_id?: number;
}) =>
  request<ComunicazioneInterna>("/dashboard/comunicazioni", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(input),
  });
export const assegnaComunicazioneInterna = (
  id: number,
  assegnato_a_id: number | null,
) =>
  request<ComunicazioneInterna>(
  `/dashboard/comunicazioni/${id}/assegnazione?` +
    new URLSearchParams(
      assegnato_a_id === null ? {} : { assegnato_a_id: String(assegnato_a_id) },
    ),
  { method: "PATCH" },
  );
export const getPrenotazioni = () =>
  demo()
    ? Promise.resolve(mockPrenotazioni)
    : request<Prenotazione[]>("/prenotazioni");
export async function getFlotta(sedeId?: number): Promise<Veicolo[]> {
  if (demo()) {
    return sedeId === undefined
      ? mockVeicoli
      : mockVeicoli.filter((vehicle) => vehicle.sede_id === sedeId);
  }
  const response = await request<DashboardFlotta | Veicolo[]>(
    sedeId === undefined
      ? "/dashboard/flotta"
      : `/dashboard/flotta?sede_id=${sedeId}`,
  );
  return Array.isArray(response) ? response : response.veicoli;
}
export async function getDashboardFlotta(
  sedeId?: number,
): Promise<DashboardFlotta> {
  if (demo()) {
    const veicoli =
      sedeId === undefined
        ? mockVeicoli
        : mockVeicoli.filter((vehicle) => vehicle.sede_id === sedeId);
    return {
      sede_id: sedeId ?? null,
      veicoli_totali: veicoli.length,
      veicoli_per_stato: veicoli.reduce<Record<string, number>>(
        (counts, vehicle) => {
          counts[vehicle.stato] = (counts[vehicle.stato] ?? 0) + 1;
          return counts;
        },
        {},
      ),
      veicoli,
      prenotazioni: mockPrenotazioni.filter((booking) =>
        veicoli.some((vehicle) => vehicle.id === booking.veicolo_id),
      ),
    };
  }
  return request<DashboardFlotta>(
    sedeId === undefined
      ? "/dashboard/flotta"
      : `/dashboard/flotta?sede_id=${sedeId}`,
  );
}
export async function cercaVeicoliDisponibili(
  sedeId: number,
  da: string,
  a: string,
  tipo?: string,
) {
  if (demo()) {
    return mockVeicoli.filter(
      (vehicle) =>
        vehicle.sede_id === sedeId &&
        vehicle.stato === "disponibile" &&
        (!tipo || vehicle.tipo === tipo),
    );
  }
  const params = new URLSearchParams({
    sede_id: String(sedeId),
    da: new Date(da).toISOString(),
    a: new Date(a).toISOString(),
  });
  if (tipo) params.set("tipo", tipo);
  return request<Veicolo[]>(`/veicoli/disponibili?${params}`);
}
export const getClienti = () =>
  demo()
    ? Promise.resolve(
        Array.from({ length: 12 }, (_, index) => ({ id: index + 10 })),
      )
    : request<ClienteRiferimento[]>("/clienti");
export async function getFermi(sedeId?: number): Promise<FermoVeicolo[]> {
  if (demo()) {
    return mockVeicoli
        .filter(
          (vehicle) =>
            (sedeId === undefined || vehicle.sede_id === sedeId) &&
            (vehicle.stato === "in_manutenzione" || vehicle.stato === "danneggiato"),
        )
        .map((veicolo, index) => {
          const giorni_fermo = 3 + index * 2;
          return {
            veicolo,
            giorni_fermo,
            priorita: (veicolo.stato === "danneggiato" ? 100 : 50) + giorni_fermo,
            motivo:
              veicolo.stato === "danneggiato"
                ? "Danno segnalato"
                : "Manutenzione necessaria",
          };
        })
        .sort((a, b) => b.priorita - a.priorita);
  }
  return request<FermoVeicolo[]>(
    sedeId === undefined
      ? "/dashboard/fermi"
      : `/dashboard/fermi?sede_id=${sedeId}`,
  );
}
export async function rientroServizio(veicoloId: number) {
  if (demo()) {
      const vehicle = mockVeicoli.find((item) => item.id === veicoloId);
      if (vehicle) vehicle.stato = "disponibile";
      return vehicle;
  }
  return request<Veicolo>(`/veicoli/${veicoloId}/rientro-servizio`, {
      method: "POST",
  });
}
export async function creaPrenotazione(input: {
  veicolo_id: number;
  cliente_id?: number;
  inizio: string;
  fine: string;
}) {
  if (demo()) {
    const prenotazione: Prenotazione = {
      id: (mockPrenotazioni[0]?.id ?? 0) + 1,
      veicolo_id: input.veicolo_id,
      cliente_id: input.cliente_id ?? 10,
      inizio: new Date(input.inizio).toISOString(),
      fine: new Date(input.fine).toISOString(),
      stato: "confermata",
    };
    mockPrenotazioni.unshift(prenotazione);
    const vehicle = mockVeicoli.find((item) => item.id === input.veicolo_id);
    if (vehicle) vehicle.stato = "prenotato";
    return prenotazione;
  }
  return request<Prenotazione>("/prenotazioni", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...input,
      inizio: new Date(input.inizio).toISOString(),
      fine: new Date(input.fine).toISOString(),
    }),
  });
}
export async function creaManutenzione(
  veicoloId: number,
  input: { descrizione: string; stato: string },
) {
  if (demo()) {
    const vehicle = mockVeicoli.find((item) => item.id === veicoloId);
    if (vehicle) vehicle.stato = "in_manutenzione";
    return vehicle;
  }
  return request(`/veicoli/${veicoloId}/manutenzioni`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, inizio: new Date().toISOString() }),
  });
}
export async function creaTrasferimento(
  veicoloId: number,
  input: { sede_destinazione_id: number; note: string },
) {
  if (demo()) {
    const vehicle = mockVeicoli.find((item) => item.id === veicoloId);
    if (vehicle) vehicle.stato = "in_trasferimento";
    return vehicle;
  }
  return request(`/veicoli/${veicoloId}/trasferimenti`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...input,
      stato: "programmato",
      inizio: new Date().toISOString(),
    }),
  });
}
export async function registraIspezione(
  prenotazioneId: number,
  fase: "checkin" | "checkout",
  input: IspezioneInput,
) {
  if (demo()) {
    const booking = mockPrenotazioni.find((item) => item.id === prenotazioneId);
    if (booking) booking.stato = fase === "checkin" ? "in_corso" : "conclusa";
    if (fase === "checkout") {
      const vehicle = mockVeicoli.find(
        (item) => item.id === booking?.veicolo_id,
      );
      if (vehicle) vehicle.stato = "disponibile";
    }
    return booking;
  }
  return request<Prenotazione>(`/prenotazioni/${prenotazioneId}/${fase}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}
export async function setStatoVeicolo(id: number, stato: string) {
  if (demo()) {
    const vehicle = mockVeicoli.find((item) => item.id === id);
    if (vehicle) vehicle.stato = stato;
    return vehicle;
  }
  return request<Veicolo>(`/veicoli/${id}/stato`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stato }),
  });
}
