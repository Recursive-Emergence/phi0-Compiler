"""
Earth Engine Router
================
FastAPI router for Earth Engine data processing operations.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import redis

from backend.api.database import get_db
from backend.models.database import DataProcessingTask, GridCell
from backend.data_processors.earth_engine.pipeline import EarthEnginePipeline
from backend.core.agent_self_model.model import REAgentSelfModel
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Redis client for task tracking
redis_client = redis.from_url(settings.REDIS_URL)

# Pydantic models
class BoundingBox(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    
class ProcessRegionRequest(BaseModel):
    bounding_box: BoundingBox
    data_sources: Optional[List[str]] = None
    max_cells: Optional[int] = 100

class ProcessCellsRequest(BaseModel):
    cell_ids: List[str]
    data_sources: Optional[List[str]] = None

class TaskStatus(BaseModel):
    task_id: int
    status: str
    progress: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Helper function to get agent self-model
def get_agent_model(db: Session = Depends(get_db)):
    try:
        return REAgentSelfModel(db, redis_client)
    except Exception as e:
        logger.error(f"Failed to initialize agent model: {e}")
        return None

# Background task functions
def process_region_background(
    request: ProcessRegionRequest,
    db: Session,
    task_id: int
):
    """Background task to process a region"""
    try:
        # Create session for background task
        pipeline = EarthEnginePipeline(db, get_agent_model(db))
        
        # Process region
        results = pipeline.process_region(
            bounding_box=[
                request.bounding_box.min_lon,
                request.bounding_box.min_lat,
                request.bounding_box.max_lon,
                request.bounding_box.max_lat
            ],
            data_sources=request.data_sources,
            max_cells=request.max_cells
        )
        
        # Store results in Redis (for faster access)
        redis_client.setex(
            f"earth_engine:task:{task_id}", 
            86400,  # 24 hour expiration
            str(results)
        )
    except Exception as e:
        logger.error(f"Background task failed: {e}")
        # Store error in Redis
        redis_client.setex(
            f"earth_engine:task:{task_id}", 
            86400,
            str({"error": str(e)})
        )

def process_cells_background(
    request: ProcessCellsRequest,
    db: Session,
    task_id: int
):
    """Background task to process specific cells"""
    try:
        # Create session for background task
        pipeline = EarthEnginePipeline(db, get_agent_model(db))
        
        # Process cells
        results = pipeline.process_cells_batch(
            cell_ids=request.cell_ids,
            data_sources=request.data_sources
        )
        
        # Store results in Redis
        redis_client.setex(
            f"earth_engine:task:{task_id}", 
            86400,
            str(results)
        )
    except Exception as e:
        logger.error(f"Background task failed: {e}")
        # Store error in Redis
        redis_client.setex(
            f"earth_engine:task:{task_id}", 
            86400,
            str({"error": str(e)})
        )

# Endpoints
@router.get("/earth-engine/status")
def check_earth_engine_status(db: Session = Depends(get_db)):
    """
    Check Earth Engine connection status
    """
    pipeline = EarthEnginePipeline(db)
    connections_status = pipeline.check_connections()
    
    # Get authentication details
    from backend.data_processors.earth_engine.auth import get_authentication_status
    auth_status = get_authentication_status()
    
    if not connections_status["earth_engine"]:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error", 
                "message": "Earth Engine connection failed",
                "auth_status": auth_status
            }
        )
    
    if not connections_status["database"]:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Database connection failed"}
        )
    
    return {
        "status": "ok", 
        "connections": connections_status, 
        "auth_details": auth_status
    }

@router.post("/earth-engine/process-region", response_model=TaskStatus)
def process_region(
    request: ProcessRegionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start processing all cells in a region with Earth Engine
    """
    # Create task record
    task = DataProcessingTask(
        task_type="region_processing",
        status="queued",
        params={
            "bounding_box": [
                request.bounding_box.min_lon,
                request.bounding_box.min_lat,
                request.bounding_box.max_lon,
                request.bounding_box.max_lat
            ],
            "data_sources": request.data_sources,
            "max_cells": request.max_cells
        }
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Start background task
    background_tasks.add_task(
        process_region_background,
        request=request,
        db=db,
        task_id=task.id
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "progress": 0.0
    }

@router.post("/earth-engine/process-cells", response_model=TaskStatus)
def process_cells(
    request: ProcessCellsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start processing specific cells with Earth Engine
    """
    # Validate cell IDs
    valid_cells = db.query(GridCell).filter(GridCell.cell_id.in_(request.cell_ids)).all()
    valid_ids = [cell.cell_id for cell in valid_cells]
    
    if not valid_ids:
        raise HTTPException(status_code=404, detail="No valid cell IDs found")
    
    # Create task record
    task = DataProcessingTask(
        task_type="batch_processing",
        status="queued",
        params={
            "cell_ids": valid_ids,
            "data_sources": request.data_sources
        }
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Start background task
    background_tasks.add_task(
        process_cells_background,
        request=ProcessCellsRequest(cell_ids=valid_ids, data_sources=request.data_sources),
        db=db,
        task_id=task.id
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "progress": 0.0
    }

@router.get("/earth-engine/task/{task_id}", response_model=TaskStatus)
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Check the status of an Earth Engine processing task
    """
    # Try to get status from Redis (faster)
    redis_result = redis_client.get(f"earth_engine:task:{task_id}")
    
    if redis_result:
        # Parse Redis result
        try:
            redis_data = eval(redis_result.decode('utf-8'))
            if isinstance(redis_data, dict):
                if "error" in redis_data:
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "error": redis_data["error"]
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "results": redis_data
                    }
        except Exception as e:
            logger.error(f"Error parsing Redis result: {e}")
    
    # Fall back to database
    task = db.query(DataProcessingTask).filter(DataProcessingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    response = {
        "task_id": task.id,
        "status": task.status
    }
    
    if task.status == "completed" and task.results:
        response["results"] = task.results
    elif task.status == "failed" and task.error_message:
        response["error"] = task.error_message
    elif task.status == "running" and task.results:
        # Calculate approximate progress if available
        if isinstance(task.results, dict):
            if "processed_cells" in task.results and "total_cells" in task.results:
                total = task.results["total_cells"]
                processed = task.results["processed_cells"]
                if total > 0:
                    response["progress"] = processed / total

    return response

@router.get("/earth-engine/process-cell/{cell_id}")
def process_single_cell(
    cell_id: str,
    db: Session = Depends(get_db),
    agent_model: REAgentSelfModel = Depends(get_agent_model)
):
    """
    Process a single cell synchronously (for small requests)
    """
    # Validate cell ID
    cell = db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail=f"Cell {cell_id} not found")
    
    # Process cell
    pipeline = EarthEnginePipeline(db, agent_model)
    results = pipeline.process_cell_complete(cell_id)
    
    return results

@router.get("/earth-engine/datasets")
def get_earth_engine_datasets():
    """
    Get information about the Earth Engine datasets used in the application
    """
    datasets = [
        {
            "id": "COPERNICUS/S2_SR",
            "name": "Sentinel-2 Surface Reflectance",
            "description": "Sentinel-2 is an Earth observation mission developed by ESA as part of the Copernicus Programme to perform terrestrial observations in support of various services.",
            "resolution": "10m, 20m, 60m (band dependent)",
            "temporal_coverage": "2015-present",
            "used_for": "NDVI calculation, vegetation analysis"
        },
        {
            "id": "LARSE/GEDI/GEDI04_A_002",
            "name": "GEDI Level 4A Footprint Level Aboveground Biomass Density",
            "description": "The Global Ecosystem Dynamics Investigation (GEDI) produces high resolution laser ranging observations of the 3D structure of the Earth.",
            "resolution": "25m",
            "temporal_coverage": "2019-present",
            "used_for": "Canopy height estimation"
        },
        {
            "id": "USGS/SRTMGL1_003",
            "name": "SRTM Digital Elevation Data 1 Arc-Second",
            "description": "The Shuttle Radar Topography Mission (SRTM) digital elevation data is an international research effort that obtained digital elevation models on a near-global scale.",
            "resolution": "30m",
            "temporal_coverage": "2000",
            "used_for": "Terrain analysis, elevation, slope calculation"
        },
        {
            "id": "JRC/GSW1_3/GlobalSurfaceWater",
            "name": "JRC Global Surface Water Mapping Layers",
            "description": "The Global Surface Water dataset contains maps of the location and temporal distribution of surface water from 1984 to 2019.",
            "resolution": "30m",
            "temporal_coverage": "1984-2019",
            "used_for": "Water proximity analysis, hydrological features"
        },
        {
            "id": "LANDSAT/LC08/C02/T1_L2",
            "name": "Landsat 8 Collection 2 Tier 1 Level-2 Data",
            "description": "Landsat 8 Collection 2 Tier 1 atmospherically corrected surface reflectance.",
            "resolution": "30m",
            "temporal_coverage": "2013-present",
            "used_for": "Backup for NDVI calculation when Sentinel-2 data is unavailable"
        }
    ]
    
    return {"datasets": datasets}
