import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  ArrowRightLeft,
  Bike,
  Car,
  CalendarClock,
  Gauge,
  LogOut,
  Search,
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
  cercaVeicoliDisponibili,
  assegnaComunicazioneInterna,
  creaComunicazioneInterna,
  creaManutenzione,
  creaPrenotazione,
  creaTrasferimento,
  getDashboardFlotta,
  getClienti,
  getComunicazioniInterne,
  getOperatori,
  getFermi,
  getMe,
  getPrenotazioni,
  registraIspezione,
  rientroServizio,
  setStatoVeicolo,
  type FermoVeicolo,
  type ComunicazioneInterna,
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
const formatDataOra = (valore: string) =>
  new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(valore));
const TipoIcon = ({ tipo }: { tipo: string }) =>
  tipo === "ebike" ? (
    <Bike className="h-4 w-4" />
  ) : tipo === "furgone" ? (
    <Truck className="h-4 w-4" />
  ) : (
    <Car className="h-4 w-4" />
  );
type OperativitaSezione =
  | "prenotazioni"
  | "fermi"
  | "manutenzioni"
  | "trasferimenti"
  | "comunicazioni";

function Dashboard() {
  const session = useSession();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: getMe });
  const isStaff =
    me.data?.ruolo === "admin" ||
    me.data?.ruolo === "operatore" ||
    me.data?.ruolo === "ceo";
  const canOperate =
    me.data?.ruolo === "admin" || me.data?.ruolo === "operatore";
  const [sede, setSede] = useState<number>(1);
  const [operativita, setOperativita] =
    useState<OperativitaSezione>("prenotazioni");
  const sedeAttiva =
    me.data?.ruolo === "operatore" && me.data.sede_id ? me.data.sede_id : sede;
  const ambitoDashboard =
    me.data?.ruolo === "ceo" ? undefined : sedeAttiva;
  const flotta = useQuery({
    queryKey: ["flotta", ambitoDashboard],
    queryFn: () => getDashboardFlotta(ambitoDashboard),
    enabled: isStaff && (me.data?.ruolo === "ceo" || !!sedeAttiva),
  });
  const fermi = useQuery({
    queryKey: ["fermi", ambitoDashboard],
    queryFn: () => getFermi(ambitoDashboard),
    enabled: isStaff && (me.data?.ruolo === "ceo" || !!sedeAttiva),
  });
  const pren = useQuery({
    queryKey: ["prenotazioni"],
    queryFn: getPrenotazioni,
    enabled: me.data?.ruolo === "cliente",
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

  const v: Veicolo[] = flotta.data?.veicoli ?? [];
  const prenotazioni = isStaff
    ? (flotta.data?.prenotazioni ?? [])
    : (pren.data ?? []);
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
          {isStaff && (
            <div className="ml-4 space-y-1 border-l border-sidebar-border pl-3 pt-1">
              {[
                ["prenotazioni", "Prenotazioni operative"],
                ["fermi", "Mezzi fermi e priorità"],
                ["manutenzioni", "Manutenzioni"],
                ["trasferimenti", "Trasferimenti"],
                ["comunicazioni", "Comunicazioni interne"],
              ].map(([sezione, titolo]) => (
                <button
                  key={sezione}
                  type="button"
                  onClick={() =>
                    setOperativita(sezione as OperativitaSezione)
                  }
                  className={`block w-full rounded-md px-3 py-2 text-left text-xs transition-colors hover:bg-sidebar-accent ${
                    operativita === sezione
                      ? "bg-sidebar-accent font-medium text-sidebar-primary"
                      : "text-sidebar-foreground/70"
                  }`}
                >
                  {titolo}
                </button>
              ))}
            </div>
          )}
        </nav>
        {me.data?.ruolo === "admin" && (
          <>
            <div className="mt-8 text-xs uppercase tracking-wider text-sidebar-foreground/50">
              Sedi
            </div>
            <div className="mt-2 space-y-1 text-sm">
              {SEDI.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSede(s.id)}
                  className={`block w-full rounded-md px-3 py-2 text-left transition-colors hover:bg-sidebar-accent ${sedeAttiva === s.id ? "text-sidebar-primary" : ""}`}
                >
                  {s.nome}
                </button>
              ))}
            </div>
          </>
        )}
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
              {me.data?.ruolo === "ceo"
                ? "Tutte le sedi"
                : SEDI.find((s) => s.id === sedeAttiva)?.nome ??
                  `Sede ${sedeAttiva}`}
            </h1>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <select
              className="rounded-md border bg-card px-3 py-2 text-sm"
              value={sedeAttiva}
              disabled={me.data?.ruolo !== "admin"}
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

        {(flotta.error || fermi.error || pren.error) && (
          <p className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {(flotta.error ?? fermi.error ?? pren.error)?.message}
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
              {prenotazioni.slice(0, 7).map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between py-2"
                >
                  <div>
                    <div className="font-medium">
                      #{p.id} · veicolo {p.veicolo_id}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDataOra(p.inizio)} → {formatDataOra(p.fine)}
                    </div>
                  </div>
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-xs capitalize">
                    {label(p.stato)}
                  </span>
                </li>
              ))}
              {prenotazioni.length === 0 && (
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
                      {canOperate ? (
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
        {isStaff && (
          <>
            <OperativitaNav
              attiva={operativita}
              onChange={setOperativita}
              className="md:hidden"
            />
            {operativita === "comunicazioni" ? (
              <ComunicazioniInterne
                canOperate={canOperate}
                ruolo={me.data?.ruolo ?? ""}
                userId={me.data?.id ?? 0}
                veicoli={v}
              />
            ) : operativita === "fermi" ? (
              <FermiOperations
                fermi={fermi.data ?? []}
                canOperate
                onChanged={() => {
                  void flotta.refetch();
                  void fermi.refetch();
                }}
              />
            ) : canOperate && sedeAttiva ? (
              <MvpOperations
                sezione={operativita}
                sedeId={sedeAttiva}
                sedi={SEDI}
                prenotazioni={prenotazioni}
                onChanged={() => {
                  void flotta.refetch();
                  void pren.refetch();
                }}
              />
            ) : null}
          </>
        )}
        {!canOperate && (
          <FermiOperations
            fermi={fermi.data ?? []}
            canOperate={false}
            onChanged={() => {
              void flotta.refetch();
              void fermi.refetch();
            }}
          />
        )}
      </main>
    </div>
  );
}

function OperativitaNav({
  attiva,
  onChange,
  className,
}: {
  attiva: OperativitaSezione;
  onChange: (sezione: OperativitaSezione) => void;
  className?: string;
}) {
  const sezioni: {
    id: OperativitaSezione;
    titolo: string;
    descrizione: string;
    icona: React.ReactNode;
  }[] = [
    {
      id: "prenotazioni",
      titolo: "Prenotazioni operative",
      descrizione: "Disponibilità, prenotazioni e check-in/out",
      icona: <CalendarClock className="h-4 w-4" />,
    },
    {
      id: "fermi",
      titolo: "Mezzi fermi e priorità",
      descrizione: "Danni, anzianità del fermo e rientro in servizio",
      icona: <AlertTriangle className="h-4 w-4" />,
    },
    {
      id: "manutenzioni",
      titolo: "Manutenzioni",
      descrizione: "Pianifica e aggiorna gli interventi",
      icona: <Wrench className="h-4 w-4" />,
    },
    {
      id: "trasferimenti",
      titolo: "Trasferimenti",
      descrizione: "Sposta i mezzi tra le sedi",
      icona: <ArrowRightLeft className="h-4 w-4" />,
    },
  ];

  return (
    <section
      aria-label="Sezioni operative"
      className={`space-y-3 ${className ?? ""}`}
    >
      <div>
        <h2 className="font-display text-xl font-bold">Operatività</h2>
        <p className="text-sm text-muted-foreground">
          Seleziona l’attività da gestire nella sede attiva.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {sezioni.map((sezione) => (
          <button
            key={sezione.id}
            type="button"
            onClick={() => onChange(sezione.id)}
            className={`rounded-xl border p-4 text-left transition-colors ${
              attiva === sezione.id
                ? "border-primary bg-primary/10"
                : "bg-card hover:bg-muted/50"
            }`}
          >
            <span className="flex items-center gap-2 font-semibold">
              {sezione.icona}
              {sezione.titolo}
            </span>
            <span className="mt-2 block text-xs text-muted-foreground">
              {sezione.descrizione}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function FermiOperations({
  fermi,
  canOperate,
  onChanged,
}: {
  fermi: FermoVeicolo[];
  canOperate: boolean;
  onChanged: () => void;
}) {
  const [inCorso, setInCorso] = useState<number | null>(null);
  const [errore, setErrore] = useState("");

  async function rientra(veicoloId: number) {
    setInCorso(veicoloId);
    setErrore("");
    try {
      await rientroServizio(veicoloId);
      onChanged();
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Rientro non riuscito",
      );
    } finally {
      setInCorso(null);
    }
  }

  return (
    <Card title="Mezzi fermi e priorità">
      <p className="mb-3 text-sm text-muted-foreground">
        I danni hanno priorità sui fermi di manutenzione; a parità di urgenza
        viene mostrato prima il mezzo fermo da più tempo.
      </p>
      {fermi.length === 0 ? (
        <p className="py-2 text-sm text-muted-foreground">
          Nessun mezzo fermo in questa sede.
        </p>
      ) : (
        <ul className="divide-y">
          {fermi.map((fermo) => (
            <li
              key={fermo.veicolo.id}
              className="flex flex-wrap items-center justify-between gap-3 py-3"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-2 py-1 text-xs font-semibold ${
                    fermo.veicolo.stato === "danneggiato"
                      ? "bg-destructive/10 text-destructive"
                      : "bg-warning/15 text-warning"
                  }`}
                >
                  P{fermo.priorita}
                </span>
                <div>
                  <div className="font-medium">
                    {fermo.veicolo.targa} · {fermo.veicolo.tipo}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {fermo.motivo} · fermo da {fermo.giorni_fermo}{" "}
                    {fermo.giorni_fermo === 1 ? "giorno" : "giorni"}
                  </div>
                </div>
              </div>
              {canOperate && <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={inCorso === fermo.veicolo.id}
                onClick={() => void rientra(fermo.veicolo.id)}
              >
                {inCorso === fermo.veicolo.id
                  ? "Aggiornamento…"
                  : "Ritorna in servizio"}
              </Button>}
            </li>
          ))}
        </ul>
      )}
      {errore && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {errore}
        </p>
      )}
    </Card>
  );
}

function ComunicazioniInterne({
  canOperate,
  ruolo,
  userId,
  veicoli,
}: {
  canOperate: boolean;
  ruolo: string;
  userId: number;
  veicoli: Veicolo[];
}) {
  const qc = useQueryClient();
  const comunicazioni = useQuery({
    queryKey: ["comunicazioni-interne"],
    queryFn: getComunicazioniInterne,
  });
  const operatori = useQuery({
    queryKey: ["operatori"],
    queryFn: getOperatori,
    enabled: ruolo === "admin",
  });
  const [errore, setErrore] = useState("");
  const [testo, setTesto] = useState("");
  const [veicoloId, setVeicoloId] = useState("");
  const [assegnatoA, setAssegnatoA] = useState("");

  async function crea(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrore("");
    try {
      await creaComunicazioneInterna({
        testo,
        ...(veicoloId ? { veicolo_id: Number(veicoloId) } : {}),
        ...(assegnatoA ? { assegnato_a_id: Number(assegnatoA) } : {}),
      });
      setTesto("");
      setVeicoloId("");
      setAssegnatoA("");
      await qc.invalidateQueries({ queryKey: ["comunicazioni-interne"] });
    } catch (error) {
      setErrore(error instanceof Error ? error.message : "Invio non riuscito");
    }
  }

  const assegna = useMutation({
    mutationFn: ({
      id,
      operatoreId,
    }: {
      id: number;
      operatoreId: number | null;
    }) => assegnaComunicazioneInterna(id, operatoreId),
    onSuccess: () =>
      void qc.invalidateQueries({ queryKey: ["comunicazioni-interne"] }),
    onError: (error) =>
      setErrore(error instanceof Error ? error.message : "Assegnazione non riuscita"),
  });

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="font-display text-xl font-bold">Comunicazioni interne</h2>
        <span className="rounded-full bg-accent/30 px-2 py-0.5 text-xs">
          visibili solo alla flotta
        </span>
      </div>
      {canOperate && (
        <Card title="Nuova nota interna">
          <form className="space-y-3" onSubmit={crea}>
            <textarea
              className="min-h-24 w-full rounded-md border bg-card px-3 py-2"
              placeholder="Nota operativa, consegna o anomalia da smistare"
              value={testo}
              onChange={(event) => setTesto(event.target.value)}
              maxLength={2000}
              required
            />
            <div className="grid gap-3 md:grid-cols-2">
              <select
                className="rounded-md border bg-card px-3 py-2"
                value={veicoloId}
                onChange={(event) => setVeicoloId(event.target.value)}
              >
                <option value="">Nessun veicolo specifico</option>
                {veicoli.map((veicolo) => (
                  <option key={veicolo.id} value={veicolo.id}>
                    {veicolo.targa} · {veicolo.tipo}
                  </option>
                ))}
              </select>
              {ruolo === "admin" && (
                <select
                  className="rounded-md border bg-card px-3 py-2"
                  value={assegnatoA}
                  onChange={(event) => setAssegnatoA(event.target.value)}
                >
                  <option value="">Da smistare</option>
                  {(operatori.data ?? []).map((operatore) => (
                    <option key={operatore.id} value={operatore.id}>
                      Operatore #{operatore.id}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <Button type="submit">Pubblica nota interna</Button>
          </form>
        </Card>
      )}
      {(errore || comunicazioni.error) && (
        <p className="text-sm text-destructive" role="alert">
          {errore || comunicazioni.error?.message}
        </p>
      )}
      <Card title="Coda comunicazioni">
        {comunicazioni.isLoading ? (
          <p className="text-sm text-muted-foreground">Caricamento…</p>
        ) : (comunicazioni.data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuna comunicazione.</p>
        ) : (
          <ul className="space-y-3">
            {(comunicazioni.data ?? []).map((comunicazione: ComunicazioneInterna) => (
              <li key={comunicazione.id} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">
                    {comunicazione.veicolo_id
                      ? `Veicolo #${comunicazione.veicolo_id}`
                      : "Comunicazione di sede"}
                  </span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                    {comunicazione.stato}
                  </span>
                </div>
                <p className="mt-2">{comunicazione.testo}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDataOra(comunicazione.creato_il)} ·{" "}
                  {comunicazione.assegnato_a_id
                    ? `Operatore #${comunicazione.assegnato_a_id}`
                    : "non smistata"}
                </p>
                {canOperate && !comunicazione.assegnato_a_id && (
                  <Button
                    className="mt-2"
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      assegna.mutate({
                        id: comunicazione.id,
                        operatoreId: userId,
                      })
                    }
                  >
                    Prendi in carico
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}

function MvpOperations({
  sezione,
  sedeId,
  sedi,
  prenotazioni,
  onChanged,
}: {
  sezione: Exclude<OperativitaSezione, "fermi" | "comunicazioni">;
  sedeId: number;
  sedi: { id: number; nome: string }[];
  prenotazioni: Prenotazione[];
  onChanged: () => void;
}) {
  const clienti = useQuery({ queryKey: ["clienti"], queryFn: getClienti });
  const [inizio, setInizio] = useState(toDateTimeLocal(1));
  const [fine, setFine] = useState(toDateTimeLocal(2));
  const [tipo, setTipo] = useState("");
  const [veicoloId, setVeicoloId] = useState("");
  const [clienteId, setClienteId] = useState("");
  const [disponibili, setDisponibili] = useState<Veicolo[]>([]);
  const [messaggio, setMessaggio] = useState("");
  const [errore, setErrore] = useState("");

  function resetFeedback() {
    setMessaggio("");
    setErrore("");
  }

  async function cerca(event: FormEvent) {
    event.preventDefault();
    resetFeedback();
    try {
      setDisponibili(await cercaVeicoliDisponibili(sedeId, inizio, fine, tipo));
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Ricerca non riuscita",
      );
    }
  }

  async function prenota(event: FormEvent) {
    event.preventDefault();
    resetFeedback();
    try {
      await creaPrenotazione({
        veicolo_id: Number(veicoloId),
        cliente_id: clienteId ? Number(clienteId) : undefined,
        inizio,
        fine,
      });
      setMessaggio("Prenotazione creata.");
      setVeicoloId("");
      onChanged();
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Prenotazione non riuscita",
      );
    }
  }

  async function manutenzione(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    const form = new FormData(event.currentTarget);
    try {
      await creaManutenzione(Number(form.get("veicolo_id")), {
        descrizione: String(form.get("descrizione")),
        stato: String(form.get("stato")),
      });
      setMessaggio("Manutenzione registrata.");
      event.currentTarget.reset();
      onChanged();
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Operazione non riuscita",
      );
    }
  }

  async function trasferimento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    const form = new FormData(event.currentTarget);
    try {
      await creaTrasferimento(Number(form.get("veicolo_id")), {
        sede_destinazione_id: Number(form.get("sede_destinazione_id")),
        note: String(form.get("note")),
      });
      setMessaggio("Trasferimento registrato.");
      event.currentTarget.reset();
      onChanged();
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Operazione non riuscita",
      );
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="font-display text-xl font-bold">
          {sezione === "prenotazioni"
            ? "Prenotazioni operative"
            : sezione === "manutenzioni"
              ? "Manutenzioni"
              : "Trasferimenti"}
        </h2>
        <span className="rounded-full bg-accent/30 px-2 py-0.5 text-xs">
          sede attiva
        </span>
      </div>
      {(messaggio || errore) && (
        <p
          role="status"
          className={`rounded-md px-4 py-3 text-sm ${errore ? "bg-destructive/10 text-destructive" : "bg-success/10 text-success"}`}
        >
          {errore || messaggio}
        </p>
      )}
      {sezione === "prenotazioni" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Ricerca disponibilità">
          <form className="space-y-3" onSubmit={cerca}>
            <label className="block text-sm">
              Da
              <input
                className="mt-1 w-full rounded-md border bg-card px-3 py-2"
                type="datetime-local"
                value={inizio}
                onChange={(event) => setInizio(event.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              A
              <input
                className="mt-1 w-full rounded-md border bg-card px-3 py-2"
                type="datetime-local"
                value={fine}
                onChange={(event) => setFine(event.target.value)}
                required
              />
            </label>
            <select
              className="w-full rounded-md border bg-card px-3 py-2"
              value={tipo}
              onChange={(event) => setTipo(event.target.value)}
            >
              <option value="">Tutti i tipi</option>
              <option value="auto">Auto</option>
              <option value="furgone">Furgoni</option>
              <option value="ebike">E-bike</option>
            </select>
            <Button type="submit">
              <Search className="h-4 w-4" /> Cerca
            </Button>
          </form>
          {disponibili.length > 0 && (
            <ul className="mt-4 divide-y text-sm">
              {disponibili.map((vehicle) => (
                <li
                  key={vehicle.id}
                  className="flex items-center justify-between gap-2 py-2"
                >
                  <span>
                    #{vehicle.id} · {vehicle.tipo} · {vehicle.targa}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setVeicoloId(String(vehicle.id))}
                  >
                    Prenota
                  </Button>
                </li>
              ))}
            </ul>
          )}
          </Card>

          <Card title="Prenotazione rapida">
          <form className="space-y-3" onSubmit={prenota}>
            <input
              className="w-full rounded-md border bg-card px-3 py-2"
              type="number"
              min="1"
              placeholder="ID veicolo"
              value={veicoloId}
              onChange={(event) => setVeicoloId(event.target.value)}
              required
            />
            <select
              className="w-full rounded-md border bg-card px-3 py-2"
              value={clienteId}
              onChange={(event) => setClienteId(event.target.value)}
              required
            >
              <option value="">Seleziona cliente</option>
              {(clienti.data ?? []).map((cliente) => (
                <option key={cliente.id} value={cliente.id}>
                  Cliente #{cliente.id}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              {formatDataOra(inizio)} → {formatDataOra(fine)}
            </p>
            <Button type="submit">Crea prenotazione</Button>
          </form>
          </Card>
        </div>
      )}

      {sezione === "manutenzioni" && (
        <Card title="Registra manutenzione">
          <form className="space-y-3" onSubmit={manutenzione}>
            <input
              className="w-full rounded-md border bg-card px-3 py-2"
              name="veicolo_id"
              type="number"
              min="1"
              placeholder="ID veicolo"
              required
            />
            <input
              className="w-full rounded-md border bg-card px-3 py-2"
              name="descrizione"
              placeholder="Descrizione manutenzione"
              defaultValue="Controllo ordinario"
              required
            />
            <select
              className="w-full rounded-md border bg-card px-3 py-2"
              name="stato"
            >
              <option value="programmata">Programmata</option>
              <option value="in_corso">In corso</option>
              <option value="completata">Completata</option>
            </select>
            <Button type="submit" variant="outline">
              <Wrench className="h-4 w-4" /> Registra manutenzione
            </Button>
          </form>
        </Card>
      )}

      {sezione === "trasferimenti" && (
        <Card title="Registra trasferimento">
          <form
            className="mt-4 space-y-3 border-t pt-4"
            onSubmit={trasferimento}
          >
            <input
              className="w-full rounded-md border bg-card px-3 py-2"
              name="veicolo_id"
              type="number"
              min="1"
              placeholder="ID veicolo"
              required
            />
            <select
              className="w-full rounded-md border bg-card px-3 py-2"
              name="sede_destinazione_id"
            >
              {sedi
                .filter((sede) => sede.id !== sedeId)
                .map((sede) => (
                  <option key={sede.id} value={sede.id}>
                    {sede.nome}
                  </option>
                ))}
            </select>
            <input
              className="w-full rounded-md border bg-card px-3 py-2"
              name="note"
              placeholder="Note trasferimento"
              defaultValue="Trasferimento programmato"
            />
            <Button type="submit" variant="outline">
              <ArrowRightLeft className="h-4 w-4" /> Registra trasferimento
            </Button>
          </form>
        </Card>
      )}
      {sezione === "prenotazioni" && (
        <Card title="Prenotazioni operative">
          {prenotazioni.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessuna prenotazione attiva.
            </p>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {prenotazioni.slice(0, 8).map((booking) => (
                <li key={booking.id} className="rounded-lg border p-3 text-sm">
                  <div className="font-medium">
                    #{booking.id} · veicolo {booking.veicolo_id}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatDataOra(booking.inizio)} →{" "}
                    {formatDataOra(booking.fine)}
                  </div>
                  <InspectionForm booking={booking} onChanged={onChanged} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </section>
  );
}

function InspectionForm({
  booking,
  onChanged,
}: {
  booking: Prenotazione;
  onChanged: () => void;
}) {
  const fase = booking.stato === "in_corso" ? "checkout" : "checkin";
  const [km, setKm] = useState("");
  const [danni, setDanni] = useState(false);
  const [errore, setErrore] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setErrore("");
    try {
      await registraIspezione(booking.id, fase, {
        km: Number(km),
        danni_rilevati: danni,
      });
      onChanged();
    } catch (error) {
      setErrore(
        error instanceof Error ? error.message : "Ispezione non riuscita",
      );
    }
  }

  return (
    <form
      className="mt-3 flex flex-wrap items-end gap-2"
      onSubmit={(event) => void submit(event)}
    >
      <label className="text-xs">
        Km
        <input
          className="mt-1 w-24 rounded-md border bg-card px-2 py-1"
          type="number"
          min="0"
          value={km}
          onChange={(event) => setKm(event.target.value)}
          required
        />
      </label>
      {fase === "checkout" && (
        <label className="flex items-center gap-1 text-xs">
          <input
            type="checkbox"
            checked={danni}
            onChange={(event) => setDanni(event.target.checked)}
          />
          Danni
        </label>
      )}
      <Button type="submit" size="sm" variant="outline">
        {fase === "checkin" ? "Check-in" : "Check-out"}
      </Button>
      {errore && <span className="text-xs text-destructive">{errore}</span>}
    </form>
  );
}

function toDateTimeLocal(offsetDays: number) {
  const date = new Date(Date.now() + offsetDays * 86400000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
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
                    {formatDataOra(booking.inizio)} →{" "}
                    {formatDataOra(booking.fine)}
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
