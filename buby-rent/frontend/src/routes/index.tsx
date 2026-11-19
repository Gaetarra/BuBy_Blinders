import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Buby Rent — Gestione noleggi" },
      { name: "description", content: "Area riservata Buby Rent per flotta, prenotazioni e sedi." },
      { property: "og:title", content: "Buby Rent — Gestione noleggi" },
      { property: "og:description", content: "Area riservata Buby Rent per flotta, prenotazioni e sedi." },
    ],
  }),
  beforeLoad: () => {
    throw redirect({ to: "/login" });
  },
});
