import os

DEV_SECRET = "dev-secret-non-usare-in-produzione"
DEV_ENCRYPTION_KEY = "sWNVrAd6w3geUFBEpC_szVX7CYnnl-Cbo4IjLnK59aA="
DEV_BLIND_KEY = "dev-blind-index-key-non-usare-in-produzione"


class Settings:
    environment: str = os.getenv("ENVIRONMENT") or "development"
    database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./dev.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    secret_key: str = os.getenv("SECRET_KEY") or DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES") or "60")

    # cifratura dei dati personali: la PRIMA chiave cifra, tutte servono per decifrare
    encryption_keys: list[str] = [
        k.strip()
        for k in (os.getenv("ENCRYPTION_KEYS") or DEV_ENCRYPTION_KEY).split(",")
        if k.strip()
    ]
    blind_index_key: str = os.getenv("BLIND_INDEX_KEY") or DEV_BLIND_KEY

    # alla registrazione, collega l'account all'anagrafica importata con la stessa email.
    # Senza verifica dell'email e insicuro: in produzione e spento di default.
    collega_clienti_importati: bool = (
        os.getenv("COLLEGA_CLIENTI_IMPORTATI")
        or ("false" if (os.getenv("ENVIRONMENT") or "development") == "production" else "true")
    ).lower() == "true"

    # posta: l'API accoda le email in uscita, il worker le spedisce e legge la casella
    smtp_host: str = os.getenv("SMTP_HOST") or "localhost"
    smtp_port: int = int(os.getenv("SMTP_PORT") or "1025")
    smtp_user: str = os.getenv("SMTP_USER") or ""
    smtp_password: str = os.getenv("SMTP_PASSWORD") or ""
    smtp_starttls: bool = (os.getenv("SMTP_STARTTLS") or "false").lower() == "true"
    mail_from: str = os.getenv("MAIL_FROM") or "noreply@buby.it"
    inbox_address: str = os.getenv("INBOX_ADDRESS") or "assistenza@buby.it"
    mailpit_url: str = (os.getenv("MAILPIT_URL") or "http://localhost:8025").rstrip("/")
    poll_seconds: int = int(os.getenv("POLL_SECONDS") or "15")

    privacy_versione: str = "1.0"  # versione dell'informativa accettata alla registrazione

    admin_email: str = os.getenv("ADMIN_EMAIL") or "admin@buby.it"
    admin_password: str = os.getenv("ADMIN_PASSWORD") or "admin12345"
    operatore_password: str = os.getenv("OPERATORE_PASSWORD") or "operatore12345"


settings = Settings()
