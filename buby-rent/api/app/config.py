import os

DEV_SECRET = "dev-secret-non-usare-in-produzione"
DEV_ENCRYPTION_KEY = "sWNVrAd6w3geUFBEpC_szVX7CYnnl-Cbo4IjLnK59aA="
DEV_BLIND_KEY = "dev-blind-index-key-non-usare-in-produzione"


def parse_cors_origins(value: str | None) -> list[str]:
    origins = [origin.strip().rstrip("/") for origin in (value or "").split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS deve contenere origini esplicite, non '*'.")
    return origins or ["http://localhost:3000"]


class Settings:
    environment: str = os.getenv("ENVIRONMENT") or "development"
    database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./dev.db"
    cors_origins: list[str] = parse_cors_origins(os.getenv("CORS_ORIGINS"))
    api_log_file: str = os.getenv("API_LOG_FILE") or "logs/api.log"
    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_publishable_key: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY") or None

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

    privacy_versione: str = "1.0"  # versione dell'informativa accettata alla registrazione

    admin_email: str = os.getenv("ADMIN_EMAIL") or "admin@buby.it"
    admin_password: str = os.getenv("ADMIN_PASSWORD") or "admin12345"
    operatore_password: str = os.getenv("OPERATORE_PASSWORD") or "operatore12345"
    ceo_email: str = os.getenv("CEO_EMAIL") or "buby@buby.it"
    ceo_password: str = os.getenv("CEO_PASSWORD") or "buby12345"
    smtp_host: str = os.getenv("SMTP_HOST") or "localhost"
    smtp_port: int = int(os.getenv("SMTP_PORT") or "1025")
    smtp_user: str = os.getenv("SMTP_USER") or ""
    smtp_password: str = os.getenv("SMTP_PASSWORD") or ""
    smtp_starttls: bool = (os.getenv("SMTP_STARTTLS") or "false").lower() == "true"
    mail_from: str = os.getenv("MAIL_FROM") or "noreply@buby.it"
    poll_seconds: int = int(os.getenv("POLL_SECONDS") or "15")


settings = Settings()
