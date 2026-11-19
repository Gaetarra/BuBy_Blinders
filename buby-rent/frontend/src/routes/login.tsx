import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Car, Bike, Truck, Lock, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_URL, ApiError, login } from "@/lib/api";
import { demoToken, getSession, setToken } from "@/lib/auth";
import { isSupabaseConfigured } from "@/lib/supabase";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Accedi — Buby Rent" },
      {
        name: "description",
        content: "Accedi all'area operatori e clienti di Buby Rent.",
      },
      { property: "og:title", content: "Accedi — Buby Rent" },
      {
        property: "og:description",
        content: "Accedi all'area operatori e clienti di Buby Rent.",
      },
    ],
  }),
  beforeLoad: () => {
    if (getSession()) throw redirect({ to: "/dashboard" });
  },
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [unreachable, setUnreachable] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(email, password);
      setToken(token);
      navigate({ to: "/dashboard", replace: true });
    } catch (err) {
      setUnreachable(err instanceof ApiError && err.status === 0);
      setError(
        err instanceof ApiError && err.status === 401
          ? "Email o password errate"
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }

  function enterDemo() {
    setToken(demoToken("admin"), true);
    navigate({ to: "/dashboard", replace: true });
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-brand p-12 text-sidebar-foreground lg:flex">
        <div className="flex items-center gap-2 font-display text-xl font-bold">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-accent-foreground">
            B
          </span>
          Buby Rent
        </div>
        <div>
          <h1 className="max-w-md text-5xl font-bold leading-tight">
            La flotta giusta,{" "}
            <span className="text-accent">nella sede giusta.</span>
          </h1>
          <p className="mt-4 max-w-sm text-sidebar-foreground/70">
            Auto, furgoni ed e-bike su tutte le sedi: prenotazioni, check-in,
            manutenzioni e trasferimenti in un'unica area.
          </p>
        </div>
        <div className="flex gap-3 text-sidebar-foreground/60">
          {[Car, Truck, Bike].map((I, i) => (
            <span
              key={i}
              className="grid h-12 w-12 place-items-center rounded-xl border border-sidebar-border"
            >
              <I className="h-5 w-5" />
            </span>
          ))}
        </div>
        <div className="pointer-events-none absolute -right-24 -bottom-24 h-80 w-80 rounded-full border-[40px] border-accent/10" />
      </aside>

      <main className="flex items-center justify-center p-6">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-6">
          <div>
            <div className="mb-6 flex items-center gap-2 font-display text-lg font-bold lg:hidden">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
                B
              </span>
              Buby Rent
            </div>
            <h2 className="text-3xl font-bold">Accedi</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {isSupabaseConfigured
                ? "Accedi con il tuo account Supabase Buby Rent."
                : "Usa le credenziali del tuo account Buby Rent."}
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operatore@buby.it"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <p
              role="alert"
              className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" size="lg" disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Lock className="h-4 w-4" />
            )}
            Accedi
          </Button>
          <div className="space-y-2 border-t pt-4 text-center">
            <Button
              type="button"
              variant={unreachable ? "secondary" : "ghost"}
              className="w-full"
              onClick={enterDemo}
            >
              Entra in modalità demo
            </Button>
            <p className="text-xs text-muted-foreground">
              API: {API_URL} · token conservato solo in memoria
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
