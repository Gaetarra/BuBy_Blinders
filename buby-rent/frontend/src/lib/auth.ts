// JWT session kept in memory only (per project docs: safer than localStorage).
import { useSyncExternalStore } from "react";
import { supabase } from "./supabase";

export type JwtPayload = {
  sub: string;
  ruolo?: string;
  role?: string;
  iat?: number;
  exp: number;
};
export type Session = { token: string; payload: JwtPayload; demo: boolean };

let session: Session | null = null;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export function decodeJwt(token: string): JwtPayload {
  const part = token.split(".")[1];
  if (!part) throw new Error("Token malformato");
  const json = atob(
    part
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(part.length / 4) * 4, "="),
  );
  const p = JSON.parse(json) as JwtPayload;
  if (!p.exp || !p.sub) throw new Error("Token senza sub/exp");
  return p;
}

export function isExpired(p: JwtPayload, now = Date.now()) {
  return p.exp * 1000 <= now;
}

export function setToken(token: string, demo = false) {
  session = { token, payload: decodeJwt(token), demo };
  emit();
}

export function getSession(): Session | null {
  if (session && isExpired(session.payload)) {
    session = null;
    emit();
  }
  return session;
}

export function logout() {
  session = null;
  emit();
  return supabase?.auth.signOut().then(({ error }) => {
    if (error) throw error;
  });
}

export function useSession() {
  return useSyncExternalStore(
    (l) => (listeners.add(l), () => listeners.delete(l)),
    getSession,
    () => null,
  );
}

supabase?.auth.onAuthStateChange((_event, authSession) => {
  if (authSession) setToken(authSession.access_token);
  else {
    session = null;
    emit();
  }
});

const b64 = (o: object) =>
  btoa(JSON.stringify(o))
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
export function demoToken(ruolo = "admin") {
  const now = Math.floor(Date.now() / 1000);
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: "1", ruolo, iat: now, exp: now + 3600 })}.demo`;
}
