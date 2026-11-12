import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bike,
  Car,
  CalendarClock,
  Gauge,
  LogOut,
  Truck,
  Wrench,
  AlertTriangle,
  LayoutDashboard,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  getFlotta,
  getMe,
  getPrenotazioni,
  setStatoVeicolo,
  type Prenotazione,
  type Veicolo,
} from "@/lib/api";
import { getSession, logout, useSession } from "@/lib/auth";
import { SEDI } from "@/lib/mock";

export const Route = createFileRoute("/dashboard")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Dashboard flotta — Buby Rent" },
      {
        name: "description",
        content: "Stato della flotta, utilizzo e prenotazioni per sede.",
      },
      { property: "og:title", content: "Dashboard flotta — Buby Rent" },
      {
        property: "og:description",
        content: "Stato della flotta, utilizzo e prenotazioni per sede.",
      },
    ],
  }),
  beforeLoad: () => {
    if (!getSession()) throw redirect({ to: "/login" });
  },
  component: Dashboard,
});

const STATI = [
  "disponibile",
  "prenotato",
  "noleggiato",
  "in_manutenzione",
  "danneggiato",
  "in_trasferimento",
];
const STATO_COLOR: Record<string, string> = {
  disponibile: "var(--success)",
  prenotato: "var(--info)",
  noleggiato: "var(--primary)",
  in_manutenzione: "var(--warning)",
  danneggiato: "var(--destructive)",
  in_trasferimento: "var(--accent)",
};
const label = (s: string) => s.replace("_", " ");
const TipoIcon = ({ tipo }: { tipo: string }) =>
  tipo === "ebike" ? (
    <Bike className="h-4 w-4" />
  ) : tipo === "furgone" ? (
    <Truck className="h-4 w-4" />
  ) : (
    <Car className="h-4 w-4" />
  );

function Dashboard() {
  const session = useSession();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: getMe });
  const isStaff = me.data?.ruolo === "admin" || me.data?.ruolo === "operatore";
  const [sede, setSede] = useState<number>(1);
  const sedeAttiva =
    me.data?.ruolo === "operatore" && me.data.sede_id ? me.data.sede_id : sede;
  const flotta = useQuery({
    queryKey: ["flotta", sedeAttiva],
    queryFn: () => getFlotta(sedeAttiva),
    enabled: isStaff,
  });
  const pren = useQuery({
    queryKey: ["prenotazioni"],
    queryFn: getPrenotazioni,
    enabled: Boolean(me.data),
  });
  const cambia = useMutation({
    mutationFn: ({ id, stato }: { id: number; stato: string }) =>
      setStatoVeicolo(id, stato),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flotta"] }),
  });

  async function esci() {
    await qc.cancelQueries();
    qc.clear();
    try {
      await logout();
    } finally {
      navigate({ to: "/login", replace: true });
    }
  }

  const v: Veicolo[] = flotta.data ?? [];
  const count = (s: string) => v.filter((x) => x.stato === s).length;
  const utilizzo = v.length
    ? Math.round(((count("noleggiato") + count("prenotato")) / v.length) * 100)
    : 0;
  const fermo = count("in_manutenzione") + count("danneggiato");
  const perStato = STATI.map((s) => ({
    name: label(s),
    key: s,
    value: count(s),
  })).filter((d) => d.value);
  const perTipo = ["auto", "furgone", "ebike"].map((t) => ({
    tipo: t,
    totale: v.filter((x) => x.tipo === t).length,
  }));

  if (me.data?.ruolo === "cliente") {
    return (
      <CustomerDashboard
        email={me.data.email}
        prenotazioni={pren.data ?? []}
        isLoading={pren.isLoading}
        error={pren.error?.message}
        onLogout={() => void esci()}
      />
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col bg-sidebar p-5 text-sidebar-foreground md:flex">
        <div className="flex items-center gap-2 font-display text-lg font-bold">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            B
          </span>
          Buby Rent
        </div>
        <nav className="mt-8 space-y-1 text-sm">
          <span className="flex items-center gap-2 rounded-md bg-sidebar-accent px-3 py-2 font-medium">
            <LayoutDashboard className="h-4 w-4" /> Dashboard
          </span>
        </nav>
        <div className="mt-8 text-xs uppercase tracking-wider text-sidebar-foreground/50">
          Sedi
        </div>
        <div className="mt-2 space-y-1 text-sm">
          {SEDI.map((s) => (
            <button
              key={s.id}
              disabled={me.data?.ruolo === "operatore"}
              onClick={() => setSede(s.id)}
              className={`block w-full rounded-md px-3 py-2 text-left transition-colors hover:bg-sidebar-accent disabled:opacity-50 ${sedeAttiva === s.id ? "text-sidebar-primary" : ""}`}
            >
              {s.nome}
            </button>
          ))}
        </div>
        <div className="mt-auto space-y-3 border-t border-sidebar-border pt-4 text-sm">
          <div>
            <div className="truncate font-medium">{me.data?.email ?? "…"}</div>
            <div className="text-xs capitalize text-sidebar-foreground/60">
              {me.data?.ruolo ??
                session?.payload.ruolo ??
                session?.payload.role}{" "}
              {session?.demo && "· demo"}
            </div>
          </div>
          <button
            onClick={esci}
            className="flex items-center gap-2 text-sidebar-foreground/70 hover:text-sidebar-foreground"
          >
            <LogOut className="h-4 w-4" /> Esci
          </button>
        </div>
      </aside>

      <main className="flex-1 space-y-6 p-6 lg:p-8">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Sede</p>
            <h1 className="text-3xl font-bold">
              {SEDI.find((s) => s.id === sedeAttiva)?.nome ??
                `Sede ${sedeAttiva}`}
            </h1>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <select
              className="rounded-md border bg-card px-3 py-2 text-sm"
              value={sede}
              onChange={(e) => setSede(Number(e.target.value))}
            >
              {SEDI.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
            <Button variant="outline" size="sm" onClick={esci}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {(flotta.error || pren.error) && (
          <p className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {(flotta.error ?? pren.error)?.message}
          </p>
        )}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi
            icon={<Car className="h-5 w-5" />}
            label="Veicoli in sede"
            value={v.length}
          />
          <Kpi
            icon={<Gauge className="h-5 w-5" />}
            label="Utilizzo flotta"
            value={`${utilizzo}%`}
            highlight
          />
          <Kpi
            icon={<CalendarClock className="h-5 w-5" />}
            label="Disponibili ora"
            value={count("disponibile")}
          />
          <Kpi
            icon={<Wrench className="h-5 w-5" />}
            label="In fermo"
            value={fermo}
            warn={fermo > 0}
          />
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <Card title="Stato della flotta">
            <div className="h-56">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={perStato}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                  >
                    {perStato.map((d) => (
                      <Cell key={d.key} fill={STATO_COLOR[d.key]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="grid grid-cols-2 gap-1 text-xs">
              {perStato.map((d) => (
                <li key={d.key} className="flex items-center gap-2 capitalize">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: STATO_COLOR[d.key] }}
                  />
                  {d.name}{" "}
                  <span className="ml-auto font-medium">{d.value}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Mezzi per tipo">
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={perTipo}>
                  <XAxis dataKey="tipo" tickLine={false} axisLine={false} />
                  <YAxis
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                    width={24}
                  />
                  <Tooltip cursor={{ fill: "var(--muted)" }} />
                  <Bar
                    dataKey="totale"
                    fill="var(--primary)"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Ultime prenotazioni">
            <ul className="divide-y text-sm">
              {(pren.data ?? []).slice(0, 7).map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between py-2"
                >
                  <div>
                    <div className="font-medium">
                      #{p.id} · veicolo {p.veicolo_id}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(p.inizio).toLocaleDateString("it-IT")} →{" "}
                      {new Date(p.fine).toLocaleDateString("it-IT")}
                    </div>
                  </div>
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-xs capitalize">
                    {label(p.stato)}
                  </span>
                </li>
              ))}
              {pren.data?.length === 0 && (
                <li className="py-2 text-muted-foreground">
                  Nessuna prenotazione
                </li>
              )}
            </ul>
          </Card>
        </section>

        <Card title="Flotta">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="py-2">Tipo</th>
                  <th>Targa</th>
                  <th>Km</th>
                  <th>Stato</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {v.map((x) => (
                  <tr key={x.id}>
                    <td className="py-2">
                      <span className="flex items-center gap-2 capitalize">
                        <TipoIcon tipo={x.tipo} />
                        {x.tipo}
                      </span>
                    </td>
                    <td className="font-mono">{x.targa}</td>
                    <td>{x.km.toLocaleString("it-IT")}</td>
                    <td>
                      {isStaff ? (
                        <select
                          className="rounded-md border bg-card px-2 py-1 text-xs capitalize"
                          value={x.stato}
                          onChange={(e) =>
                            cambia.mutate({ id: x.id, stato: e.target.value })
                          }
                        >
                          {STATI.map((s) => (
                            <option key={s} value={s}>
                              {label(s)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="capitalize">{label(x.stato)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {flotta.isLoading && (
              <p className="py-4 text-muted-foreground">Caricamento…</p>
            )}
          </div>
          {cambia.error && (
            <p className="mt-3 flex items-center gap-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              {cambia.error.message}
            </p>
          )}
        </Card>
      </main>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  highlight,
  warn,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  highlight?: boolean;
  warn?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-5 shadow-card ${highlight ? "bg-brand text-primary-foreground" : "bg-card"}`}
    >
      <div
        className={`flex items-center justify-between text-sm ${highlight ? "text-primary-foreground/70" : "text-muted-foreground"}`}
      >
        {label}
        <span
          className={warn ? "text-warning" : highlight ? "text-accent" : ""}
        >
          {icon}
        </span>
      </div>
      <div className="mt-3 font-display text-3xl font-bold">{value}</div>
    </div>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border bg-card p-5 shadow-card">
      <h3 className="mb-4 font-semibold">{title}</h3>
      {children}
    </div>
  );
}

function CustomerDashboard({
  email,
  prenotazioni,
  isLoading,
  error,
  onLogout,
}: {
  email: string;
  prenotazioni: Prenotazione[];
  isLoading: boolean;
  error: string | undefined;
  onLogout: () => void;
}) {
  return (
    <main className="mx-auto min-h-screen w-full max-w-4xl space-y-6 p-6 lg:p-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{email}</p>
          <h1 className="text-3xl font-bold">Le mie prenotazioni</h1>
        </div>
        <Button variant="outline" onClick={onLogout}>
          <LogOut className="h-4 w-4" /> Esci
        </Button>
      </header>
      {error && (
        <p
          role="alert"
          className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          {error}
        </p>
      )}
      <Card title="Storico noleggi">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Caricamento…</p>
        ) : prenotazioni.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Non hai ancora prenotazioni.
          </p>
        ) : (
          <ul className="divide-y">
            {prenotazioni.map((booking) => (
              <li
                key={booking.id}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <div>
                  <div className="font-medium">
                    Prenotazione #{booking.id} · veicolo {booking.veicolo_id}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(booking.inizio).toLocaleDateString("it-IT")} →{" "}
                    {new Date(booking.fine).toLocaleDateString("it-IT")}
                  </div>
                </div>
                <span className="rounded-full bg-secondary px-2 py-0.5 text-xs capitalize">
                  {label(booking.stato)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </main>
  );
}
