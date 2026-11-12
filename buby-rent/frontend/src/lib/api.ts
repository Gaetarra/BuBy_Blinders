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
export const getPrenotazioni = () =>
  demo()
    ? Promise.resolve(mockPrenotazioni)
    : request<Prenotazione[]>("/prenotazioni");
export async function getFlotta(sedeId: number): Promise<Veicolo[]> {
  if (demo())
    return mockVeicoli.filter((vehicle) => vehicle.sede_id === sedeId);
  const response = await request<{ veicoli?: Veicolo[] } | Veicolo[]>(
    `/dashboard/flotta?sede_id=${sedeId}`,
  );
  return Array.isArray(response) ? response : (response.veicoli ?? []);
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
