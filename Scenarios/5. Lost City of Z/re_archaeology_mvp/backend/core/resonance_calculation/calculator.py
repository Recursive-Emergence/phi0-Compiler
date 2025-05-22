import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging
from backend.models.database import Psi0Attractor
from shapely.geometry import Point
import geopandas as gpd
from shapely import wkb
from geoalchemy2.shape import to_shape

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResonanceCalculator:
    """
    Implements φ⁰ Resonance Calculation for archaeological site potential scoring.
    
    This class combines contradiction field values with attractor influences
    to calculate the overall resonance score for each grid cell.
    """
    
    def __init__(self, db_session: Session):
        """Initialize the resonance calculator"""
        self.db = db_session
        
        # Load attractors from database
        self.attractors = self._load_attractors()
        
    def _load_attractors(self) -> List[Dict[str, Any]]:
        """Load psi0 attractors from the database"""
        attractors = []
        try:
            db_attractors = self.db.query(Psi0Attractor).all()
            for attractor in db_attractors:
                # Convert geometry to shapely object
                geom = to_shape(attractor.geom)
                
                attractors.append({
                    "id": attractor.id,
                    "name": attractor.attractor_name,
                    "type": attractor.attractor_type,
                    "strength": attractor.strength,
                    "influence_radius": attractor.influence_radius,
                    "point": geom,
                    "metadata": attractor.symbolic_metadata
                })
            logger.info(f"Loaded {len(attractors)} psi0 attractors")
        except Exception as e:
            logger.error(f"Failed to load attractors: {e}")
        
        return attractors
    
    def calculate_attractor_influence(self, cell_coordinates: Tuple[float, float]) -> float:
        """
        Calculate the influence of attractors on a specific cell
        
        Args:
            cell_coordinates: (longitude, latitude) of the cell centroid
            
        Returns:
            Attractor influence strength (0.0 to 1.0)
        """
        if not self.attractors:
            return 0.0
            
        cell_point = Point(cell_coordinates)
        total_influence = 0.0
        
        for attractor in self.attractors:
            # Calculate distance to attractor
            distance = cell_point.distance(attractor["point"])
            
            # Convert distance to degrees (approximate)
            # Only apply influence within the radius
            if distance <= attractor["influence_radius"]:
                # Linear decay with distance
                influence = attractor["strength"] * (1.0 - (distance / attractor["influence_radius"]))
                total_influence += influence
                
        # Cap total influence at 1.0
        return min(total_influence, 1.0)
    
    def calculate_confidence_interval(self, contradiction_strength: float, 
                                    attractor_influence: float, 
                                    evidence_count: int) -> float:
        """
        Calculate confidence interval for the resonance result
        
        Higher confidence (smaller interval) comes from:
        1. More contradictions detected
        2. Higher contradiction strength
        3. Higher attractor influence
        """
        # Base interval represents uncertainty
        base_interval = 0.4
        
        # Evidence reduces uncertainty
        evidence_factor = 1.0 - min(evidence_count / 10.0, 0.8)
        
        # Strong contradictions or attractor influence increase certainty
        strength_factor = 1.0 - (contradiction_strength * 0.3 + attractor_influence * 0.2)
        
        # Calculate the final interval
        interval = base_interval * evidence_factor * strength_factor
        
        return interval
    
    def calculate_phi0_score(self, 
                             contradiction_results: Dict[str, Any], 
                             cell_coordinates: Tuple[float, float]) -> Dict[str, Any]:
        """
        Calculate φ⁰ resonance score for a grid cell
        
        Args:
            contradiction_results: Results from contradiction detection
            cell_coordinates: (longitude, latitude) of the cell centroid
            
        Returns:
            Dictionary with resonance score and metadata
        """
        # Extract contradiction strength
        contradiction_strength = contradiction_results.get("overall_strength", 0.0)
        contradictions = contradiction_results.get("contradictions", [])
        
        # Calculate attractor influence
        attractor_influence = self.calculate_attractor_influence(cell_coordinates)
        
        # Base resonance calculation (simplified version)
        # In a full implementation, this would involve more complex interactions
        base_score = contradiction_strength * 0.7 + attractor_influence * 0.3
        
        # Apply modifiers based on contradiction types
        modifiers = 0.0
        for contradiction in contradictions:
            if contradiction["type"] == "geometric_pattern":
                modifiers += 0.15  # Geometric patterns are strong indicators
            elif contradiction["type"] == "water_proximity":
                modifiers += 0.1   # Water proximity patterns are good indicators
        
        # Apply modifiers (capped)
        final_score = min(base_score + modifiers, 1.0)
        
        # Calculate confidence interval
        confidence_interval = self.calculate_confidence_interval(
            contradiction_strength, 
            attractor_influence,
            len(contradictions)
        )
        
        # Determine site type prediction
        site_type = self._predict_site_type(contradictions, final_score)
        
        return {
            "phi0_score": final_score,
            "confidence_interval": confidence_interval,
            "site_type_prediction": site_type,
            "calculation_metadata": {
                "contradiction_strength": contradiction_strength,
                "attractor_influence": attractor_influence,
                "modifiers": modifiers,
                "contradiction_count": len(contradictions)
            }
        }
    
    def _predict_site_type(self, contradictions: List[Dict[str, Any]], score: float) -> str:
        """Predict the type of archaeological site based on contradictions and score"""
        if score < 0.3:
            return "unlikely"
            
        # Check for specific contradiction patterns
        for c in contradictions:
            if c["type"] == "geometric_pattern" and c["strength"] > 0.7:
                return "settlement"
            elif c["type"] == "water_proximity" and c["strength"] > 0.8:
                return "ceremonial_center"
                
        # Default classifications based on score
        if score >= 0.7:
            return "major_settlement"
        elif score >= 0.5:
            return "minor_settlement"
        else:
            return "potential_site"
