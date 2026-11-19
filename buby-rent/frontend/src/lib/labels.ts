export const STATO_VEICOLO: Record<string, { label: string; tone: string }> = {
  disponibile: { label: "Disponibile", tone: "bg-success/12 text-success" },
  prenotato: { label: "Prenotato", tone: "bg-info/12 text-info" },
  noleggiato: { label: "Noleggiato", tone: "bg-primary/12 text-primary" },
  in_manutenzione: { label: "In manutenzione", tone: "bg-warning/15 text-accent-foreground" },
  danneggiato: { label: "Danneggiato", tone: "bg-destructive/12 text-destructive" },
  in_trasferimento: { label: "In trasferimento", tone: "bg-secondary/12 text-secondary" },
};
export const STATO_PREN: Record<string, string> = {
  richiesta: "Richiesta", confermata: "Confermata", in_corso: "In corso", conclusa: "Conclusa", annullata: "Annullata",
};
export const TIPO: Record<string, string> = { auto: "Auto", furgone: "Furgone", ebike: "E-bike", moto: "Moto" };
export const RUOLO: Record<string, string> = { cliente: "Cliente", operatore: "Operatore", ceo: "Direzione", admin: "Amministratore" };
