from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import geopandas as gpd
from shapely.geometry import box, Point
import logging
from pydantic import BaseModel

from backend.api.database import get_db
from backend.models.database import GridCell

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class GridCellBase(BaseModel):
    cell_id: str
    geom: dict  # GeoJSON representation
    
    class Config:
        orm_mode = True

class GridCellCreate(GridCellBase):
    pass

class GridCellResponse(GridCellBase):
    id: int
    centroid: Optional[dict] = None

# Endpoints
@router.get("/grid-cells/", response_model=List[GridCellResponse])
def get_grid_cells(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    bbox: Optional[str] = Query(None, description="Bounding box in format: minLon,minLat,maxLon,maxLat")
):
    """
    Get grid cells, optionally filtered by bounding box
    """
    query = db.query(GridCell)
    
    # Apply bounding box filter if provided
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
            bounding_box = box(min_lon, min_lat, max_lon, max_lat)
            # This will use the PostGIS ST_Intersects function via GeoAlchemy
            query = query.filter(GridCell.geom.ST_Intersects(bounding_box.__geo_interface__))
        except Exception as e:
            logger.error(f"Error parsing bounding box: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid bounding box format: {e}")
    
    return query.offset(skip).limit(limit).all()

@router.get("/grid-cells/{cell_id}", response_model=GridCellResponse)
def get_grid_cell(cell_id: str, db: Session = Depends(get_db)):
    """
    Get a specific grid cell by ID
    """
    grid_cell = db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
    if not grid_cell:
        raise HTTPException(status_code=404, detail="Grid cell not found")
    return grid_cell

@router.post("/grid-cells/", response_model=GridCellResponse)
def create_grid_cell(grid_cell: GridCellCreate, db: Session = Depends(get_db)):
    """
    Create a new grid cell
    """
    try:
        # Convert GeoJSON to WKB for database storage
        from geoalchemy2.shape import from_shape
        from shapely.geometry import shape
        
        geom_shape = shape(grid_cell.geom)
        centroid = geom_shape.centroid
        
        db_grid_cell = GridCell(
            cell_id=grid_cell.cell_id,
            geom=from_shape(geom_shape),
            centroid=from_shape(centroid)
        )
        
        db.add(db_grid_cell)
        db.commit()
        db.refresh(db_grid_cell)
        return db_grid_cell
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating grid cell: {e}")
        raise HTTPException(status_code=400, detail=f"Error creating grid cell: {e}")

@router.delete("/grid-cells/{cell_id}")
def delete_grid_cell(cell_id: str, db: Session = Depends(get_db)):
    """
    Delete a grid cell
    """
    grid_cell = db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
    if not grid_cell:
        raise HTTPException(status_code=404, detail="Grid cell not found")
    
    db.delete(grid_cell)
    db.commit()
    return {"detail": "Grid cell deleted"}
