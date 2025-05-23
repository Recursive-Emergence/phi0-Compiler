"""
Seed Sites Router
================
FastAPI router for seed sites data operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from backend.api.database import get_db
from backend.models.database import SeedSite

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class SeedSiteResponse(BaseModel):
    id: int
    site_name: str
    site_description: Optional[str] = None
    site_type: Optional[str] = None
    confidence_level: Optional[str] = None
    longitude: float
    latitude: float
    source_reference: Optional[str] = None
    site_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

@router.get("/seed-sites/", response_model=List[SeedSiteResponse])
def get_seed_sites(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all seed sites
    """
    sites = db.query(SeedSite).offset(skip).limit(limit).all()
    
    # Convert to response format
    response = []
    for site in sites:
        # Convert the geometry to lat/lon
        point = to_shape(site.geom)
        
        # Create response object
        site_data = {
            "id": site.id,
            "site_name": site.site_name,
            "site_description": site.site_description,
            "site_type": site.site_type,
            "confidence_level": site.confidence_level,
            "longitude": point.x,
            "latitude": point.y,
            "source_reference": site.source_reference,
            "site_metadata": site.site_metadata
        }
        response.append(site_data)
    
    return response

@router.get("/seed-sites/{site_id}", response_model=SeedSiteResponse)
def get_seed_site(
    site_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific seed site by ID
    """
    site = db.query(SeedSite).filter(SeedSite.id == site_id).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Seed site not found")
    
    # Convert the geometry to lat/lon
    point = to_shape(site.geom)
    
    # Create response object
    site_data = {
        "id": site.id,
        "site_name": site.site_name,
        "site_description": site.site_description,
        "site_type": site.site_type,
        "confidence_level": site.confidence_level,
        "longitude": point.x,
        "latitude": point.y,
        "source_reference": site.source_reference,
        "site_metadata": site.site_metadata
    }
    
    return site_data
