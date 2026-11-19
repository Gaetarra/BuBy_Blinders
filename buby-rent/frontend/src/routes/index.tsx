import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";
import { getMe, loginApi, API_URL } from "@/lib/api";
import { readSession, saveSession } from "@/lib/session";
import { demoUser } from "@/lib/demo";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Accesso area riservata · Buby Rent" },
      { name: "description", content: "Accesso sicuro all'area operativa Buby Rent: flotta, prenotazioni e manutenzioni." },
      { property: "og:title", content: "Accesso area riservata · Buby Rent" },
      { property: "og:description", content: "Area operativa Buby Rent per flotta, prenotazioni e manutenzioni." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (readSession()) navigate({ to: "/dashboard" });
  }, [navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await loginApi(email.trim(), password);
      const user = await getMe(token);
      saveSession({ token, user });
      navigate({ to: "/dashboard" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accesso non riuscito");
    } finally {
      setLoading(false);
    }
  }

  function enterDemo() {
    saveSession({ token: "demo", user: demoUser, demo: true });
    navigate({ to: "/dashboard" });
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-gradient-deep text-brand-deep-foreground lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="grid-pattern absolute inset-0" aria-hidden />
        <div className="relative flex items-center gap-3">
          <Logo />
          <span className="font-display text-xl font-semibold">Buby Rent</span>
        </div>
        <div className="relative max-w-lg">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-primary">Area operativa</p>
          <h1 className="text-5xl font-semibold leading-[1.05]">La flotta giusta, nella sede giusta, al momento giusto.</h1>
          <p className="mt-6 text-lg opacity-75">Auto, furgoni, moto ed e-bike: prenotazioni, fermi e manutenzioni di tutte le sedi in un'unica vista.</p>
        </div>
        <div className="relative grid grid-cols-3 gap-6 border-t border-brand-deep-foreground/15 pt-8">
          {[["3", "Sedi attive"], ["4", "Tipi di veicolo"], ["24/7", "Monitoraggio"]].map(([n, l]) => (
            <div key={l}>
              <div className="font-display text-3xl font-semibold">{n}</div>
              <div className="text-sm opacity-60">{l}</div>
            </div>
          ))}
        </div>
      </aside>

      <main className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <Logo />
            <span className="font-display text-xl font-semibold">Buby Rent</span>
          </div>
          <h2 className="text-3xl font-semibold">Accedi</h2>
          <p className="mt-2 text-sm text-muted-foreground">Usa le credenziali aziendali fornite dall'amministratore.</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <Field label="Email aziendale" icon={<Mail className="h-4 w-4" />}>
              <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="nome@bubyrent.it" className="h-full w-full bg-transparent outline-none placeholder:text-muted-foreground/60" />
            </Field>
            <Field label="Password" icon={<Lock className="h-4 w-4" />}>
              <input type={show ? "text" : "password"} required autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
                className="h-full w-full bg-transparent outline-none placeholder:text-muted-foreground/60" />
              <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Nascondi password" : "Mostra password"}
                className="text-muted-foreground hover:text-foreground">
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </Field>

            {error && <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/8 px-3 py-2.5 text-sm text-destructive">{error}</div>}

            <button type="submit" disabled={loading}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-gradient-brand font-semibold text-primary-foreground shadow-glow transition hover:brightness-110 disabled:opacity-60">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Accedi <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="h-px flex-1 bg-border" /> oppure <span className="h-px flex-1 bg-border" />
          </div>
          <button onClick={enterDemo}
            className="h-11 w-full rounded-lg border border-secondary/30 font-semibold text-secondary transition hover:bg-secondary hover:text-secondary-foreground">
            Esplora con dati dimostrativi
          </button>

          <p className="mt-10 flex items-start gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            Accesso protetto con token JWT, valido solo per questa scheda del browser. Server: {API_URL}
          </p>
        </div>
      </main>
    </div>
  );
}

function Field({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium">{label}</span>
      <span className="flex h-11 items-center gap-2.5 rounded-lg border border-input bg-card px-3 text-sm transition focus-within:border-primary focus-within:ring-4 focus-within:ring-ring/15">
        <span className="text-muted-foreground">{icon}</span>
        {children}
      </span>
    </label>
  );
}

export function Logo() {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-brand font-display text-lg font-bold text-primary-foreground shadow-glow">B</span>
  );
}
