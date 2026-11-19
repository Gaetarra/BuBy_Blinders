import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, CalendarClock, Car, LayoutDashboard, LogOut, Search, Truck, Wrench } from "lucide-react";
import { getDashboardFlotta, getFermi, setStatoVeicolo, type DashboardFlotta, type FermoVeicolo } from "@/lib/api";
import { clearSession, readSession, type Session } from "@/lib/session";
import { demoDomanda, demoFermi, demoFlotta, SEDI } from "@/lib/demo";
import { RUOLO, STATO_PREN, STATO_VEICOLO, TIPO } from "@/lib/labels";
import { Logo } from "./index";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard flotta · Buby Rent" },
      { name: "description", content: "Stato della flotta, prenotazioni, fermi e domanda per sede di Buby Rent." },
      { property: "og:title", content: "Dashboard flotta · Buby Rent" },
      { property: "og:description", content: "Flotta, prenotazioni e fermi di tutte le sedi Buby Rent." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});

const CHART = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"];
const fmt = (d: string) => new Date(d).toLocaleString("it-IT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const sede = (id: number | null) => (id == null ? "Tutte le sedi" : SEDI[id] ?? `Sede ${id}`);

function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [session, setSession] = useState<Session | null>(null);
  const [filtro, setFiltro] = useState("");

  useEffect(() => {
    const s = readSession();
    if (!s) navigate({ to: "/" });
    else setSession(s);
  }, [navigate]);

  const flotta = useQuery<DashboardFlotta>({
    queryKey: ["flotta", session?.token],
    enabled: !!session,
    queryFn: () => (session!.demo ? Promise.resolve(demoFlotta) : getDashboardFlotta(session!.token)),
  });
  const fermi = useQuery<FermoVeicolo[]>({
    queryKey: ["fermi", session?.token],
    enabled: !!session,
    queryFn: () => (session!.demo ? Promise.resolve(demoFermi) : getFermi(session!.token)),
  });
  const cambiaStato = useMutation({
    mutationFn: ({ id, stato }: { id: number; stato: string }) => {
      if (session!.demo) {
        const v = demoFlotta.veicoli.find((x) => x.id === id)!;
        v.stato = stato;
        return Promise.resolve(v);
      }
      return setStatoVeicolo(session!.token, id, stato);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flotta"] }),
  });

  useEffect(() => {
    const err = flotta.error as { status?: number } | null;
    if (err?.status === 401) { clearSession(); navigate({ to: "/" }); }
  }, [flotta.error, navigate]);

  const data = flotta.data;
  const perStato = useMemo(() => {
    const c: Record<string, number> = {};
    data?.veicoli.forEach((v) => (c[v.stato] = (c[v.stato] ?? 0) + 1));
    return c;
  }, [data]);
  const veicoli = (data?.veicoli ?? []).filter((v) =>
    `${v.targa} ${TIPO[v.tipo] ?? v.tipo} ${sede(v.sede_id)}`.toLowerCase().includes(filtro.toLowerCase()));
  const targa = (id: number) => data?.veicoli.find((v) => v.id === id)?.targa ?? `#${id}`;

  if (!session) return null;
  const tot = data?.veicoli.length ?? 0;
  const fermiCount = (perStato["in_manutenzione"] ?? 0) + (perStato["danneggiato"] ?? 0);
  const pie = Object.entries(perStato).map(([k, v]) => ({ name: STATO_VEICOLO[k]?.label ?? k, value: v }));

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-brand-deep p-5 text-brand-deep-foreground md:flex">
        <div className="flex items-center gap-3 px-2"><Logo /><span className="font-display text-lg font-semibold">Buby Rent</span></div>
        <nav className="mt-10 space-y-1 text-sm">
          {[[LayoutDashboard, "Panoramica", true], [Car, "Flotta"], [CalendarClock, "Prenotazioni"], [Wrench, "Manutenzioni"], [Truck, "Trasferimenti"]].map(([Icon, l, a]) => {
            const I = Icon as typeof Car;
            return (
              <a key={l as string} href={a ? "#" : `#${(l as string).toLowerCase()}`}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition ${a ? "bg-gradient-brand font-semibold shadow-glow" : "opacity-70 hover:bg-brand-deep-foreground/10 hover:opacity-100"}`}>
                <I className="h-4 w-4" /> {l as string}
              </a>
            );
          })}
        </nav>
        <div className="mt-auto rounded-xl bg-brand-deep-foreground/8 p-4 text-sm">
          <div className="truncate font-semibold">{session.user.email}</div>
          <div className="opacity-60">{RUOLO[session.user.ruolo] ?? session.user.ruolo} · {sede(session.user.sede_id)}</div>
          <button onClick={() => { clearSession(); navigate({ to: "/" }); }}
            className="mt-3 flex items-center gap-2 text-primary hover:brightness-125"><LogOut className="h-4 w-4" /> Esci</button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-6 py-8 lg:px-10">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">{new Date().toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" })}</p>
            <h1 className="text-3xl font-semibold">Panoramica flotta</h1>
          </div>
          <div className="flex items-center gap-3">
            {session.demo && <span className="rounded-full bg-secondary/10 px-3 py-1 text-xs font-semibold text-secondary">Dati dimostrativi</span>}
            <button onClick={() => { clearSession(); navigate({ to: "/" }); }} className="rounded-lg border px-3 py-2 text-sm md:hidden">Esci</button>
          </div>
        </header>

        {flotta.isError && (flotta.error as { status?: number })?.status !== 401 && (
          <div className="mt-6 rounded-xl border border-destructive/30 bg-destructive/8 p-4 text-sm text-destructive">{(flotta.error as Error).message}</div>
        )}

        <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi icon={Car} label="Veicoli in flotta" value={tot} hint={`${Object.keys(SEDI).length} sedi`} />
          <Kpi icon={Wrench} label="Veicoli fermi" value={fermiCount} hint="Manutenzione o danno" />
          <Kpi icon={CalendarClock} label="Prenotazioni attive" value={data?.prenotazioni.filter((p) => ["confermata", "in_corso", "richiesta"].includes(p.stato)).length ?? 0} hint="Richieste, confermate, in corso" />
        </section>

        <section className="mt-6 grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2" title="Domanda prevista per sede" subtitle="Noleggi giornalieri stimati · settimana corrente">
            <div className="h-64">
              <ResponsiveContainer>
                <AreaChart data={demoDomanda} margin={{ left: -20, right: 8 }}>
                  <defs>
                    {["torino", "milano", "stresa"].map((k, i) => (
                      <linearGradient key={k} id={`g-${k}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART[i]} stopOpacity={0.35} /><stop offset="100%" stopColor={CHART[i]} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="giorno" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid var(--border)", background: "var(--card)" }} />
                  <Area dataKey="torino" name="Torino" stroke={CHART[0]} fill="url(#g-torino)" strokeWidth={2} />
                  <Area dataKey="milano" name="Milano" stroke={CHART[1]} fill="url(#g-milano)" strokeWidth={2} />
                  <Area dataKey="stresa" name="Stresa" stroke={CHART[2]} fill="url(#g-stresa)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Stato veicoli" subtitle="Distribuzione attuale">
            <div className="h-44">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={pie} dataKey="value" innerRadius={48} outerRadius={72} paddingAngle={3} stroke="none">
                    {pie.map((_, i) => <Cell key={i} fill={CHART[i % CHART.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid var(--border)", background: "var(--card)" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-2 space-y-1.5 text-sm">
              {pie.map((p, i) => (
                <li key={p.name} className="flex items-center justify-between">
                  <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: CHART[i % CHART.length] }} />{p.name}</span>
                  <span className="font-semibold">{p.value}</span>
                </li>
              ))}
            </ul>
          </Card>
        </section>

        <section className="mt-6 grid gap-4 xl:grid-cols-3">
          <Card title="Fermi prioritari" subtitle="Veicoli da rimettere in servizio" icon={AlertTriangle}>
            <ul className="space-y-3">
              {(fermi.data ?? []).map((f) => (
                <li key={f.veicolo.id} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-display font-semibold">{f.veicolo.targa}</span>
                    <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive">{f.giorni_fermo} gg</span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{f.motivo}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{TIPO[f.veicolo.tipo] ?? f.veicolo.tipo} · {sede(f.veicolo.sede_id)}</p>
                </li>
              ))}
              {fermi.data?.length === 0 && <p className="text-sm text-muted-foreground">Nessun veicolo fermo.</p>}
            </ul>
          </Card>
          <Card className="xl:col-span-2" title="Prenotazioni" subtitle="Ultime e prossime">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr><th className="pb-3">#</th><th className="pb-3">Veicolo</th><th className="pb-3">Ritiro</th><th className="pb-3">Riconsegna</th><th className="pb-3">Stato</th></tr>
                </thead>
                <tbody>
                  {(data?.prenotazioni ?? []).slice(0, 8).map((p) => (
                    <tr key={p.id} className="border-t">
                      <td className="py-3 text-muted-foreground">{p.id}</td>
                      <td className="py-3 font-semibold">{targa(p.veicolo_id)}</td>
                      <td className="py-3">{fmt(p.inizio)}</td>
                      <td className="py-3">{fmt(p.fine)}</td>
                      <td className="py-3"><span className="rounded-full bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground">{STATO_PREN[p.stato] ?? p.stato}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </section>

        <section id="flotta" className="mt-6">
          <Card title="Flotta" subtitle="Aggiorna lo stato dei veicoli"
            action={
              <label className="flex h-9 items-center gap-2 rounded-lg border bg-background px-3 text-sm">
                <Search className="h-4 w-4 text-muted-foreground" />
                <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Cerca targa, tipo, sede" className="w-48 bg-transparent outline-none" />
              </label>
            }>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr><th className="pb-3">Targa</th><th className="pb-3">Tipo</th><th className="pb-3">Sede</th><th className="pb-3 text-right">Km</th><th className="pb-3 pl-6">Stato</th><th className="pb-3">Modifica</th></tr>
                </thead>
                <tbody>
                  {veicoli.map((v) => {
                    const s = STATO_VEICOLO[v.stato];
                    return (
                      <tr key={v.id} className="border-t">
                        <td className="py-3 font-display font-semibold">{v.targa}</td>
                        <td className="py-3">{TIPO[v.tipo] ?? v.tipo}</td>
                        <td className="py-3 text-muted-foreground">{sede(v.sede_id)}</td>
                        <td className="py-3 text-right tabular-nums">{v.km.toLocaleString("it-IT")}</td>
                        <td className="py-3 pl-6"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${s?.tone ?? "bg-muted"}`}>{s?.label ?? v.stato}</span></td>
                        <td className="py-3">
                          <select aria-label={`Stato ${v.targa}`} value={v.stato} disabled={cambiaStato.isPending}
                            onChange={(e) => cambiaStato.mutate({ id: v.id, stato: e.target.value })}
                            className="rounded-md border bg-background px-2 py-1 text-sm">
                            {Object.entries(STATO_VEICOLO).map(([k, o]) => <option key={k} value={k}>{o.label}</option>)}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {flotta.isLoading && <p className="py-6 text-center text-sm text-muted-foreground">Caricamento…</p>}
            </div>
          </Card>
        </section>
      </main>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, hint, accent }: { icon: typeof Car; label: string; value: string | number; hint: string; accent?: boolean }) {
  return (
    <div className={`rounded-2xl p-5 shadow-card ${accent ? "bg-gradient-brand text-primary-foreground" : "border bg-card"}`}>
      <div className="flex items-center justify-between">
        <span className={`text-sm ${accent ? "opacity-85" : "text-muted-foreground"}`}>{label}</span>
        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent ? "bg-primary-foreground/15" : "bg-accent text-accent-foreground"}`}><Icon className="h-4 w-4" /></span>
      </div>
      <div className="mt-3 font-display text-3xl font-semibold">{value}</div>
      <div className={`mt-1 text-xs ${accent ? "opacity-75" : "text-muted-foreground"}`}>{hint}</div>
    </div>
  );
}

function Card({ title, subtitle, children, className = "", action, icon: Icon }: { title: string; subtitle?: string; children: React.ReactNode; className?: string; action?: React.ReactNode; icon?: typeof Car }) {
  return (
    <div className={`rounded-2xl border bg-card p-5 shadow-card ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 font-semibold">{Icon && <Icon className="h-4 w-4 text-primary" />}{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}
