import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import DEV_BLIND_KEY, DEV_ENCRYPTION_KEY, DEV_SECRET, settings
from .database import Base, SessionLocal, engine
from .routers import auth, prenotazioni, veicoli
from .seed import carica_dati_mock

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    chiavi_dev = []
    if settings.secret_key == DEV_SECRET:
        chiavi_dev.append("SECRET_KEY")
    if DEV_ENCRYPTION_KEY in settings.encryption_keys:
        chiavi_dev.append("ENCRYPTION_KEYS")
    if settings.blind_index_key == DEV_BLIND_KEY:
        chiavi_dev.append("BLIND_INDEX_KEY")
    if chiavi_dev:
        if settings.environment == "production":
            raise RuntimeError(f"Chiavi di sviluppo in produzione: {', '.join(chiavi_dev)}")
        log.warning("Chiavi di sviluppo in uso (%s): impostane di vere in .env", ", ".join(chiavi_dev))
    Base.metadata.create_all(engine)  # in seguito: migrazioni con Alembic
    with SessionLocal() as db:
        carica_dati_mock(db)
    yield


app = FastAPI(title="Buby Rent API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(veicoli.router)
app.include_router(prenotazioni.router)


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
