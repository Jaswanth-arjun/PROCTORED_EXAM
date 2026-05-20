"""
ATLAS MCQ Assistant — FastAPI Application Entry Point

Starts the server with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("🚀 Starting ATLAS MCQ Assistant...")
    await init_db()
    logger.info("✅ Database initialized")
    logger.info(f"🔑 OpenAI configured: {bool(settings.OPENAI_API_KEY)}")
    logger.info(f"🌐 CORS origins: {settings.CORS_ORIGINS}")
    yield
    logger.info("👋 Shutting down ATLAS MCQ Assistant")


app = FastAPI(
    title="ATLAS MCQ Assistant",
    description="AI-powered realtime MCQ learning assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(api_router)

# WebSocket route
app.websocket("/ws")(websocket_endpoint)


@app.get("/")
async def root():
    """Root endpoint — server info."""
    return {
        "name": "ATLAS MCQ Assistant",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
