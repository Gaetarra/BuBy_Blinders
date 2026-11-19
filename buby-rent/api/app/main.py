import logging
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import DEV_BLIND_KEY, DEV_ENCRYPTION_KEY, DEV_SECRET, settings
from .database import Base, SessionLocal, engine
from .operazioni import router as operazioni_router
from .routers import auth, prenotazioni, veicoli
from .seed import carica_dati_mock

log = logging.getLogger("uvicorn.error")
api_log = logging.getLogger("buby.api")
api_log.setLevel(logging.INFO)
api_log.propagate = True

log_path = Path(settings.api_log_file)
log_path.parent.mkdir(parents=True, exist_ok=True)
resolved_log_path = str(log_path.resolve())
if not any(
    getattr(handler, "baseFilename", None) == resolved_log_path
    for handler in api_log.handlers
):
    file_handler = RotatingFileHandler(
        resolved_log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    api_log.addHandler(file_handler)


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


@app.middleware("http")
async def registra_chiamate_api(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    request_id = uuid4().hex
    started_at = time.perf_counter()
    status_code = 500
    error_type = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        duration_ms = (time.perf_counter() - started_at) * 1000
        log_method = (
            api_log.error
            if status_code >= 500
            else api_log.warning
            if status_code >= 400
            else api_log.info
        )
        log_method(
            "request_id=%s method=%s path=%s status_code=%d duration_ms=%.2f error_type=%s",
            request_id,
            request.method,
            quote(request.url.path, safe="/:@-._~"),
            status_code,
            duration_ms,
            error_type or "-",
        )


app.include_router(auth.router)
app.include_router(veicoli.router)
app.include_router(prenotazioni.router)
app.include_router(operazioni_router)


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
