import { createFileRoute, redirect } from "@tanstack/react-router";
import { Dashboard } from "../dashboard";
import { getSession } from "@/lib/auth";

export const Route = createFileRoute("/dashboard/prenotazioni")({
  ssr: false,
  beforeLoad: () => {
    if (!getSession()) throw redirect({ to: "/login" });
  },
  component: () => <Dashboard pagina="prenotazioni" />,
});
