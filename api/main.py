"""
FastAPI Main Application Server.
Run with: uvicorn api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import profile, tasks, artifacts, chat, uploads, notifications
from services.scheduler import scheduler_service


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print("[LifeScout API] Server starting up...")
    # Startup: ensure data directories exist
    from config.settings import settings
    from pathlib import Path

    for group in ["career", "life", "learning"]:
        (Path(settings.data_dir) / group / "artifacts").mkdir(parents=True, exist_ok=True)
        (Path(settings.data_dir) / group / "logs").mkdir(parents=True, exist_ok=True)
    Path(settings.checkpoints_dir).mkdir(parents=True, exist_ok=True)

    print("[LifeScout API] Data directories initialized.")
    scheduler_service.start()
    yield
    scheduler_service.shutdown()
    print("[LifeScout API] Server shutting down.")


# --- App Factory ---
app = FastAPI(
    title="LifeScout API",
    description="Backend API for the LifeScout AI personal assistant.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
# Allow the Next.js frontend (typically on port 3000) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount Routers ---
app.include_router(profile.router)
app.include_router(tasks.router)
app.include_router(artifacts.router)
app.include_router(chat.router)
app.include_router(uploads.router)
app.include_router(notifications.router)


# --- Health Check ---
@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "lifescouter-api"}
