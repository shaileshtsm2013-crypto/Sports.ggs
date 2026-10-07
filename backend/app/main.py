"""Sports Analyzer AI - Main FastAPI Application."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.database.database import init_db
from backend.app.api.camera import router as camera_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.players import router as players_router
from backend.app.api.matches import router as matches_router
from backend.app.api.chat import router as chat_router
from backend.app.api.calibration import router as calibration_router
from backend.app.api.reports import router as reports_router
from backend.app.api.optimization import router as optimization_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sports_analyzer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Sports Analyzer AI backend initialized successfully.")
    yield
    logger.info("Shutting down Sports Analyzer AI backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Cross-platform computer vision sports analysis application for Volleyball, Kabaddi, and Kho Kho.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(camera_router)
app.include_router(analysis_router)
app.include_router(players_router)
app.include_router(matches_router)
app.include_router(chat_router)
app.include_router(calibration_router)
app.include_router(reports_router)
app.include_router(optimization_router)

# Mount static web UI assets
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/app", response_class=FileResponse)
async def serve_app():
    """Serve interactive web application dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Web UI not available"}



@app.get("/")
async def root():
    """Root status and API information."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "supported_sports": ["volleyball", "kabaddi", "kho_kho"],
        "docs_url": "/docs",
        "endpoints": {
            "camera": "/api/camera",
            "analysis": "/api/analysis",
            "players": "/api/players",
            "matches": "/api/matches",
            "chat": "/api/chat",
            "reports": "/api/reports",
            "optimization": "/api/optimization"
        }
    }




@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
