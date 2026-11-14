# Email, worker e Mailpit

## Cosa fa

La conferma di una prenotazione viene accodata nella stessa transazione e
inviata da un worker separato. Mailpit consente di visualizzare le email
durante lo sviluppo senza usare destinatari reali.

## Implementazione

- `EmailDaInviare` conserva destinatario, oggetto, corpo, stato e tentativi.
- `email_uscita.py` accoda l'email senza eseguire SMTP nella richiesta API.
- `worker.py` esegue polling, invia via SMTP e applica retry fino a cinque
  tentativi.
- `docker-compose.yml` avvia API, worker e Mailpit con porte SMTP `1025` e
  web `8025`.
- L'email di prenotazione usa date italiane leggibili, mentre le API
  mantengono ISO 8601.

## Branch

`feature/email-worker-mailpit`
