// Client for the Buby Rent FastAPI backend (JWT bearer auth).
export const API_URL = (import.meta.env["VITE_API_URL"] as string | undefined)?.trim() || "http://localhost:8000";

export type Veicolo = { id: number; sede_id: number; tipo: string; targa: string; stato: string; km: number };
export type Prenotazione = { id: number; veicolo_id: number; cliente_id: number; inizio: string; fine: string; stato: string };
export type Utente = { id: number; email: string; ruolo: string; cliente_id: number | null; sede_id: number | null };
export type DashboardFlotta = {
  sede_id: number | null;
  veicoli_totali: number;
  veicoli_per_stato: Record<string, number>;
  veicoli: Veicolo[];
  prenotazioni: Prenotazione[];
};
export type FermoVeicolo = { veicolo: Veicolo; priorita: number; giorni_fermo: number; motivo: string };
export type Sede = { id: number; nome: string; citta: string };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Server non raggiungibile (${API_URL})`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = typeof body.detail === "string" ? body.detail : res.status === 401 ? "Credenziali non valide" : `Errore ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** OAuth2 password flow: returns a JWT access token. */
export async function loginApi(email: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username: email, password });
  const data = await request<{ access_token: string }>("/auth/login", null, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  return data.access_token;
}

export const getMe = (t: string) => request<Utente>("/auth/me", t);
export const getSedi = (t: string) => request<Sede[]>("/dashboard/sedi", t);

async function sedeDashboard(t: string): Promise<number | undefined> {
  const utente = await getMe(t);
  if (utente.ruolo !== "admin") return undefined;
  const sedi = await getSedi(t);
  return sedi[0]?.id;
}

export async function getDashboardFlotta(t: string, sedeIdParam?: number | null): Promise<DashboardFlotta> {
  const sedeId = sedeIdParam !== undefined ? (sedeIdParam ?? undefined) : await sedeDashboard(t);
  return request<DashboardFlotta>(
    sedeId === undefined ? "/dashboard/flotta" : `/dashboard/flotta?sede_id=${sedeId}`,
    t,
  );
}

export async function getFermi(t: string, sedeIdParam?: number | null): Promise<FermoVeicolo[]> {
  const sedeId = sedeIdParam !== undefined ? (sedeIdParam ?? undefined) : await sedeDashboard(t);
  return request<FermoVeicolo[]>(
    sedeId === undefined ? "/dashboard/fermi" : `/dashboard/fermi?sede_id=${sedeId}`,
    t,
  );
}
export const setStatoVeicolo = (t: string, id: number, stato: string) =>
  request<Veicolo>(`/veicoli/${id}/stato`, t, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stato }),
  });

/** Decode JWT payload (display only — the server is the authority). */
export function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const p = token.split(".")[1] ?? "";
    return JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}
