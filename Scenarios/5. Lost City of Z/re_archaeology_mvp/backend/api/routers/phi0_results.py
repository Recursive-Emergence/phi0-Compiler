from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import numpy as np
from pydantic import BaseModel
import logging

from backend.api.database import get_db
from backend.models.database import Phi0Result, GridCell, EnvironmentalData
from backend.core.contradiction_detection.detector import ContradictionDetector
from backend.core.resonance_calculation.calculator import ResonanceCalculator
from geoalchemy2.shape import to_shape

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class Phi0ResultBase(BaseModel):
    cell_id: str
    phi0_score: float
    confidence_interval: Optional[float] = None
    site_type_prediction: Optional[str] = None
    
    class Config:
        orm_mode = True

class Phi0ResultCreate(Phi0ResultBase):
    contradiction_patterns: Optional[Dict[str, Any]] = None
    calculation_metadata: Optional[Dict[str, Any]] = None

class Phi0ResultResponse(Phi0ResultBase):
    id: int
    contradiction_patterns: Optional[Dict[str, Any]] = None
    calculation_metadata: Optional[Dict[str, Any]] = None
    calculated_at: Optional[str] = None

class CalculationRequest(BaseModel):
    cell_ids: List[str]

# Endpoints
@router.get("/phi0-results/", response_model=List[Phi0ResultResponse])
def get_phi0_results(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    site_type: Optional[str] = None
):
    """
    Get phi0 resonance results, optionally filtered by minimum score or site type
    """
    query = db.query(Phi0Result)
    
    # Apply filters
    if min_score is not None:
        query = query.filter(Phi0Result.phi0_score >= min_score)
    
    if site_type:
        query = query.filter(Phi0Result.site_type_prediction == site_type)
    
    return query.order_by(Phi0Result.phi0_score.desc()).offset(skip).limit(limit).all()

@router.get("/phi0-results/{cell_id}", response_model=Phi0ResultResponse)
def get_phi0_result(cell_id: str, db: Session = Depends(get_db)):
    """
    Get phi0 resonance result for a specific grid cell
    """
    result = db.query(Phi0Result).filter(Phi0Result.cell_id == cell_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Phi0 result not found for this cell")
    return result

@router.post("/phi0-results/calculate", response_model=List[Phi0ResultResponse])
def calculate_phi0_results(
    request: CalculationRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate phi0 resonance scores for specified grid cells
    """
    results = []
    
    # Initialize detectors and calculators
    contradiction_detector = ContradictionDetector()
    resonance_calculator = ResonanceCalculator(db)
    
    for cell_id in request.cell_ids:
        try:
            # Get grid cell and environmental data
            grid_cell = db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
            env_data = db.query(EnvironmentalData).filter(EnvironmentalData.cell_id == cell_id).first()
            
            if not grid_cell or not env_data:
                logger.warning(f"Missing data for cell {cell_id}")
                continue
            
            # Convert DB data to python dict for processing
            cell_data = {
                "cell_id": cell_id,
                "ndvi_mean": env_data.ndvi_mean,
                "ndvi_std": env_data.ndvi_std,
                "canopy_height_mean": env_data.canopy_height_mean,
                "canopy_height_std": env_data.canopy_height_std,
                "elevation_mean": env_data.elevation_mean,
                "elevation_std": env_data.elevation_std,
                "slope_mean": env_data.slope_mean,
                "slope_std": env_data.slope_std,
                "water_proximity": env_data.water_proximity,
                # Extract NDVI matrix if available in raw_data
                "ndvi_matrix": env_data.raw_data.get("ndvi_matrix") if env_data.raw_data and "ndvi_matrix" in env_data.raw_data else None
            }
            
            # Get cell centroid coordinates
            centroid = to_shape(grid_cell.centroid)
            cell_coordinates = (centroid.x, centroid.y)
            
            # Detect contradictions
            contradiction_results = contradiction_detector.detect_all_contradictions(cell_data)
            
            # Calculate resonance (phi0 score)
            resonance_results = resonance_calculator.calculate_phi0_score(
                contradiction_results, cell_coordinates
            )
            
            # Create or update phi0 result in database
            existing_result = db.query(Phi0Result).filter(Phi0Result.cell_id == cell_id).first()
            
            if existing_result:
                # Update existing record
                existing_result.phi0_score = resonance_results["phi0_score"]
                existing_result.confidence_interval = resonance_results["confidence_interval"]
                existing_result.site_type_prediction = resonance_results["site_type_prediction"]
                existing_result.contradiction_patterns = contradiction_results
                existing_result.calculation_metadata = resonance_results["calculation_metadata"]
                db_result = existing_result
            else:
                # Create new record
                db_result = Phi0Result(
                    cell_id=cell_id,
                    phi0_score=resonance_results["phi0_score"],
                    confidence_interval=resonance_results["confidence_interval"],
                    site_type_prediction=resonance_results["site_type_prediction"],
                    contradiction_patterns=contradiction_results,
                    calculation_metadata=resonance_results["calculation_metadata"]
                )
                db.add(db_result)
            
            db.commit()
            db.refresh(db_result)
            results.append(db_result)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error calculating phi0 score for cell {cell_id}: {e}")
    
    return results

@router.get("/phi0-results/heatmap", response_model=Dict[str, Any])
def get_phi0_heatmap(
    db: Session = Depends(get_db),
    bbox: Optional[str] = Query(None, description="Bounding box in format: minLon,minLat,maxLon,maxLat"),
    min_score: float = 0.0
):
    """
    Get phi0 scores as a heatmap for visualization
    """
    query = db.query(
        Phi0Result.cell_id,
        Phi0Result.phi0_score,
        GridCell.geom,
        GridCell.centroid
    ).join(
        GridCell, Phi0Result.cell_id == GridCell.cell_id
    ).filter(
        Phi0Result.phi0_score >= min_score
    )
    
    # Apply bounding box filter if provided
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
            query = query.filter(
                GridCell.centroid.ST_X() >= min_lon,
                GridCell.centroid.ST_X() <= max_lon,
                GridCell.centroid.ST_Y() >= min_lat,
                GridCell.centroid.ST_Y() <= max_lat
            )
        except Exception as e:
            logger.error(f"Error parsing bounding box: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid bounding box format: {e}")
    
    results = query.all()
    
    # Format results for heatmap visualization
    heatmap_data = []
    for cell_id, score, geom, centroid in results:
        # Convert to GeoJSON coordinates
        centroid_shape = to_shape(centroid)
        heatmap_data.append({
            "cell_id": cell_id,
            "score": score,
            "lat": centroid_shape.y,
            "lng": centroid_shape.x,
            "weight": score  # Use score as the weight for heatmap
        })
    
    return {"data": heatmap_data}
