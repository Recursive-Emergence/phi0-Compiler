from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import redis
import logging
import os
import pathlib
from typing import Dict, List, Any

from backend.api.database import get_db
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the RE-Archaeology Agent System",
    version="0.1.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = redis.from_url(settings.REDIS_URL)

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "RE-Archaeology Agent API", "docs_url": "/docs"}

# Import and include routers
from backend.api.routers import grid_cells, environmental_data, phi0_results, discussions, map_states, earth_engine

app.include_router(grid_cells.router, prefix=settings.API_V1_STR, tags=["grid_cells"])
app.include_router(environmental_data.router, prefix=settings.API_V1_STR, tags=["environmental_data"])
app.include_router(phi0_results.router, prefix=settings.API_V1_STR, tags=["phi0_results"])
app.include_router(discussions.router, prefix=settings.API_V1_STR, tags=["discussions"])
app.include_router(map_states.router, prefix=settings.API_V1_STR, tags=["map_states"])
app.include_router(earth_engine.router, prefix=settings.API_V1_STR, tags=["earth_engine"])

# Mount static files for frontend
frontend_path = pathlib.Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    # Mount frontend at /frontend instead of root path to avoid conflict with API routes
    app.mount("/frontend", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up {settings.PROJECT_NAME} API")
    
    # Check that we can connect to database and Redis
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        logger.info("Successfully connected to the database")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    try:
        redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    # Initialize Earth Engine
    try:
        from backend.data_processors.earth_engine.connector import EarthEngineConnector
        ee_connector = EarthEngineConnector()
        if ee_connector.initialized:
            logger.info("Successfully initialized Earth Engine")
        else:
            logger.warning("Earth Engine initialization deferred - will be initialized on first use")
    except Exception as e:
        logger.error(f"Earth Engine initialization failed: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.PROJECT_NAME} API")
