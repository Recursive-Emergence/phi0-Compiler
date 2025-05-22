from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime
import uuid

from backend.api.database import get_db
from backend.models.database import MapState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class MapStateBase(BaseModel):
    state_params: Dict[str, Any]
    title: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        orm_mode = True

class MapStateCreate(MapStateBase):
    created_by: Optional[str] = "anonymous"

class MapStateResponse(MapStateBase):
    id: int
    state_id: str
    created_at: datetime
    created_by: str

# Endpoints
@router.get("/map-states/", response_model=List[MapStateResponse])
def get_map_states(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """
    Get all saved map states
    """
    return db.query(MapState).order_by(MapState.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/map-states/", response_model=MapStateResponse)
def create_map_state(
    map_state: MapStateCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new saved map state with URL-friendly ID
    """
    # Generate a URL-friendly state ID
    state_id = str(uuid.uuid4())[:8]
    
    db_map_state = MapState(
        state_id=state_id,
        **map_state.dict()
    )
    
    db.add(db_map_state)
    db.commit()
    db.refresh(db_map_state)
    
    return db_map_state

@router.get("/map-states/{state_id}", response_model=MapStateResponse)
def get_map_state(
    state_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific map state by its URL-friendly ID
    """
    map_state = db.query(MapState).filter(MapState.state_id == state_id).first()
    if not map_state:
        raise HTTPException(status_code=404, detail="Map state not found")
    
    return map_state

@router.delete("/map-states/{state_id}")
def delete_map_state(
    state_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a saved map state
    """
    map_state = db.query(MapState).filter(MapState.state_id == state_id).first()
    if not map_state:
        raise HTTPException(status_code=404, detail="Map state not found")
    
    db.delete(map_state)
    db.commit()
    
    return {"detail": "Map state deleted"}
