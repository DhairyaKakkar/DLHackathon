import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.services.seed import run_seed
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.routers import students, topics, questions, attempts, tasks, metrics, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Creating database tables …")
    create_tables()

    if settings.AUTO_SEED:
        logger.info("Auto-seeding …")
        run_seed()

    logger.info("Starting scheduler …")
    start_scheduler()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Stopping scheduler …")
    stop_scheduler()


app = FastAPI(
    title="Evidence-Aligned Learning Engine (EALE)",
    description=(
        "Measures durable understanding via Retention, Transfer, and Calibration checks. "
        "Combines them into a single Durable Understanding Score (DUS)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(students.router, prefix=PREFIX)
app.include_router(topics.router, prefix=PREFIX)
app.include_router(questions.router, prefix=PREFIX)
app.include_router(attempts.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(metrics.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "EALE API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "ok",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
