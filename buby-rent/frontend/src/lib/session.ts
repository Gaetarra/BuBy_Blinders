import type { Utente } from "./api";

export type Session = { token: string; user: Utente; demo?: boolean };
const KEY = "buby.session";

// sessionStorage: cleared when the tab closes; token never persists across browser sessions.
export function readSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    if (!s.demo) {
      const exp = JSON.parse(atob((s.token.split(".")[1] ?? "").replace(/-/g, "+").replace(/_/g, "/"))).exp;
      if (typeof exp === "number" && exp * 1000 < Date.now()) { clearSession(); return null; }
    }
    return s;
  } catch { return null; }
}
export const saveSession = (s: Session) => sessionStorage.setItem(KEY, JSON.stringify(s));
export const clearSession = () => sessionStorage.removeItem(KEY);
