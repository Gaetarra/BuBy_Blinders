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

    privacy_versione: str = "1.0"  # versione dell'informativa accettata alla registrazione

    admin_email: str = os.getenv("ADMIN_EMAIL") or "admin@buby.it"
    admin_password: str = os.getenv("ADMIN_PASSWORD") or "admin12345"
    operatore_password: str = os.getenv("OPERATORE_PASSWORD") or "operatore12345"


settings = Settings()
