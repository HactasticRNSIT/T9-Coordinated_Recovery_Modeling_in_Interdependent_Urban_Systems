from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1 import incidents, infrastructure, recovery, resilience, simulation, graph, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup: load ML models into memory
    from app.ml.model_registry import ModelRegistry
    await ModelRegistry.load_all_models()
    print(f"[UrbanSync AI] Models loaded. Environment: {settings.ENVIRONMENT}")
    yield
    # Shutdown: cleanup
    print("[UrbanSync AI] Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Coordinated Recovery Modeling in Interdependent Urban Systems",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
API_PREFIX = "/api/v1"
app.include_router(incidents.router, prefix=API_PREFIX, tags=["Incidents"])
app.include_router(infrastructure.router, prefix=API_PREFIX, tags=["Infrastructure"])
app.include_router(recovery.router, prefix=API_PREFIX, tags=["Recovery"])
app.include_router(resilience.router, prefix=API_PREFIX, tags=["Resilience"])
app.include_router(simulation.router, prefix=API_PREFIX, tags=["Simulation"])
app.include_router(graph.router, prefix=API_PREFIX, tags=["Graph"])
app.include_router(websocket.router, prefix=API_PREFIX, tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "UrbanSync AI — Coordinated Recovery Modeling",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
