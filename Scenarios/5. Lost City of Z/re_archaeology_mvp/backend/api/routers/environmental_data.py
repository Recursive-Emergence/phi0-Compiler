from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import json
import numpy as np

from backend.api.database import get_db
from backend.models.database import EnvironmentalData, GridCell

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class EnvironmentalDataBase(BaseModel):
    cell_id: str
    ndvi_mean: Optional[float] = None
    ndvi_std: Optional[float] = None
    canopy_height_mean: Optional[float] = None
    canopy_height_std: Optional[float] = None
    elevation_mean: Optional[float] = None
    elevation_std: Optional[float] = None
    slope_mean: Optional[float] = None
    slope_std: Optional[float] = None
    water_proximity: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

class EnvironmentalDataCreate(EnvironmentalDataBase):
    pass

class EnvironmentalDataResponse(EnvironmentalDataBase):
    id: int
    processed_at: str

# Endpoints
@router.get("/environmental-data/", response_model=List[EnvironmentalDataResponse])
def get_environmental_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    cell_id: Optional[str] = None
):
    """
    Get environmental data, optionally filtered by cell_id
    """
    query = db.query(EnvironmentalData)
    
    if cell_id:
        query = query.filter(EnvironmentalData.cell_id == cell_id)
    
    return query.offset(skip).limit(limit).all()

@router.get("/environmental-data/{cell_id}", response_model=EnvironmentalDataResponse)
def get_cell_environmental_data(
    cell_id: str,
    db: Session = Depends(get_db)
):
    """
    Get environmental data for a specific cell
    """
    env_data = db.query(EnvironmentalData).filter(EnvironmentalData.cell_id == cell_id).first()
    if not env_data:
        raise HTTPException(status_code=404, detail="Environmental data not found for this cell")
    
    return env_data

@router.post("/environmental-data/", response_model=EnvironmentalDataResponse)
def create_environmental_data(
    env_data: EnvironmentalDataCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update environmental data for a cell
    """
    # Check if cell exists
    cell = db.query(GridCell).filter(GridCell.cell_id == env_data.cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Grid cell not found")
    
    # Check if environmental data already exists for this cell
    existing_data = db.query(EnvironmentalData).filter(
        EnvironmentalData.cell_id == env_data.cell_id
    ).first()
    
    if existing_data:
        # Update existing record
        for key, value in env_data.dict(exclude_unset=True).items():
            setattr(existing_data, key, value)
        db_env_data = existing_data
    else:
        # Create new record
        db_env_data = EnvironmentalData(**env_data.dict())
        db.add(db_env_data)
    
    db.commit()
    db.refresh(db_env_data)
    return db_env_data

@router.post("/environmental-data/upload", response_model=Dict[str, Any])
async def upload_batch_environmental_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload batch environmental data from a JSON file
    """
    try:
        contents = await file.read()
        data = json.loads(contents)
        
        created = 0
        updated = 0
        failed = 0
        
        for item in data:
            try:
                # Check if cell exists
                cell_id = item.get("cell_id")
                if not cell_id:
                    logger.warning(f"Skipping item without cell_id")
                    failed += 1
                    continue
                
                cell = db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
                if not cell:
                    logger.warning(f"Skipping unknown cell_id: {cell_id}")
                    failed += 1
                    continue
                
                # Check if environmental data already exists for this cell
                existing_data = db.query(EnvironmentalData).filter(
                    EnvironmentalData.cell_id == cell_id
                ).first()
                
                if existing_data:
                    # Update existing record
                    for key, value in item.items():
                        if key != "id" and hasattr(existing_data, key):
                            setattr(existing_data, key, value)
                    updated += 1
                else:
                    # Create new record
                    db_env_data = EnvironmentalData(**item)
                    db.add(db_env_data)
                    created += 1
                
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                failed += 1
        
        db.commit()
        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "failed": failed
        }
    
    except Exception as e:
        logger.error(f"Error processing batch upload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid data format: {e}")

@router.delete("/environmental-data/{cell_id}")
def delete_environmental_data(
    cell_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete environmental data for a cell
    """
    env_data = db.query(EnvironmentalData).filter(EnvironmentalData.cell_id == cell_id).first()
    if not env_data:
        raise HTTPException(status_code=404, detail="Environmental data not found for this cell")
    
    db.delete(env_data)
    db.commit()
    
    return {"detail": "Environmental data deleted"}
