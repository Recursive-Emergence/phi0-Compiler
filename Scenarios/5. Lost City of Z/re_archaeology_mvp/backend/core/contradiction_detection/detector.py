import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContradictionDetector:
    """
    Implements the ψ⁰ Field Generation through contradiction detection.
    This class detects various types of contradictions in the environmental data
    that might indicate human modification of the landscape.
    """
    
    def __init__(self):
        """Initialize the contradiction detector with configuration parameters"""
        self.ndvi_canopy_threshold = settings.NDVI_CANOPY_CONTRADICTION_THRESHOLD
    
    def detect_ndvi_canopy_contradiction(self, ndvi: float, canopy_height: float) -> Tuple[bool, float]:
        """
        Detect contradiction between NDVI and canopy height
        
        In natural Amazon conditions, high NDVI typically correlates with high canopy.
        A contradiction (high NDVI, low canopy or vice versa) may indicate human intervention.
        """
        if ndvi > 0.7 and canopy_height < 10.0:  # High vegetation density but low canopy
            contradiction_strength = min(ndvi, 1.0) * (1.0 - (canopy_height / 10.0))
            return True, contradiction_strength
        elif ndvi < 0.3 and canopy_height > 20.0:  # Low vegetation density but high canopy
            contradiction_strength = (1.0 - min(ndvi, 1.0)) * (canopy_height / 30.0)
            return True, contradiction_strength
        return False, 0.0
    
    def detect_geometric_patterns(self, ndvi_matrix: np.ndarray) -> Tuple[bool, float, List[Dict]]:
        """
        Detect geometric patterns in NDVI data that might indicate human structures
        
        This is a simplified implementation. In practice, this would use more sophisticated
        image processing and pattern recognition techniques.
        """
        # This is a placeholder implementation
        # In a real implementation, this would use techniques like:
        # - Hough transforms to detect lines
        # - Frequency domain analysis (FFT) to detect regular patterns
        # - Shape detection algorithms
        
        # Simulate detection of a geometric pattern
        detected_patterns = []
        detected = False
        strength = 0.0
        
        # Check for grid-like patterns using simplified method
        # (In reality, this would be much more sophisticated)
        if ndvi_matrix.shape[0] >= 3 and ndvi_matrix.shape[1] >= 3:
            # Check for horizontal and vertical lines in the NDVI pattern
            h_diff = np.diff(ndvi_matrix, axis=0)
            v_diff = np.diff(ndvi_matrix, axis=1)
            
            # Count significant edges
            h_edges = np.sum(np.abs(h_diff) > 0.2)
            v_edges = np.sum(np.abs(v_diff) > 0.2)
            
            # Normalize by size
            total_pixels = ndvi_matrix.shape[0] * ndvi_matrix.shape[1]
            edge_density = (h_edges + v_edges) / total_pixels
            
            # Detect if edge density is suspiciously high (potential geometric pattern)
            if edge_density > 0.3:
                detected = True
                strength = min(edge_density, 1.0)
                detected_patterns.append({
                    "type": "geometric_grid",
                    "strength": strength,
                    "edge_density": edge_density
                })
        
        return detected, strength, detected_patterns
    
    def detect_water_proximity_contradiction(self, 
                                           water_proximity: float, 
                                           elevation: float,
                                           slope: float) -> Tuple[bool, float]:
        """
        Detect contradictions in water proximity and terrain
        
        Settlement patterns often show specific relationships with water bodies
        that contradict natural distribution patterns.
        """
        contradiction = False
        strength = 0.0
        
        # Ancient settlements often near water but elevated enough to avoid flooding
        if 50 < water_proximity < 500 and elevation > 5.0 and slope < 10.0:
            # Ideal settlement location: close to water, elevated, not too steep
            contradiction = True
            proximity_factor = 1.0 - (water_proximity / 500.0)
            elevation_factor = min(elevation / 20.0, 1.0)
            slope_factor = 1.0 - (slope / 10.0)
            
            # Calculate overall strength
            strength = proximity_factor * elevation_factor * slope_factor
        
        return contradiction, strength
    
    def detect_all_contradictions(self, 
                                 cell_data: Dict[str, Any], 
                                 regional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Detect all contradiction types in the provided cell data
        
        Args:
            cell_data: Dictionary containing environmental data for the cell
            regional_context: Optional dictionary with wider regional context
            
        Returns:
            Dictionary containing detected contradictions and overall ψ⁰ field strength
        """
        results = {
            "contradictions": [],
            "overall_strength": 0.0,
            "cell_id": cell_data.get("cell_id")
        }
        
        # Ensure all required data is available
        required_fields = ["ndvi_mean", "canopy_height_mean", "water_proximity", 
                          "elevation_mean", "slope_mean"]
        
        if not all(field in cell_data for field in required_fields):
            logger.warning(f"Missing required fields for contradiction detection in cell {cell_data.get('cell_id')}")
            return results
        
        # Detect NDVI-Canopy contradiction
        contradiction, strength = self.detect_ndvi_canopy_contradiction(
            cell_data["ndvi_mean"], cell_data["canopy_height_mean"]
        )
        if contradiction:
            results["contradictions"].append({
                "type": "ndvi_canopy",
                "strength": strength,
                "description": "Contradiction between vegetation density and canopy height"
            })
        
        # Detect water proximity contradiction
        contradiction, strength = self.detect_water_proximity_contradiction(
            cell_data["water_proximity"],
            cell_data["elevation_mean"],
            cell_data["slope_mean"]
        )
        if contradiction:
            results["contradictions"].append({
                "type": "water_proximity",
                "strength": strength,
                "description": "Unusual relationship between water proximity and terrain"
            })
        
        # Detect geometric patterns if NDVI matrix is available
        if "ndvi_matrix" in cell_data:
            contradiction, strength, patterns = self.detect_geometric_patterns(
                cell_data["ndvi_matrix"]
            )
            if contradiction:
                for pattern in patterns:
                    results["contradictions"].append({
                        "type": "geometric_pattern",
                        "strength": pattern["strength"],
                        "pattern_type": pattern["type"],
                        "description": "Detected geometric pattern inconsistent with natural formation"
                    })
        
        # Calculate overall contradiction strength
        if results["contradictions"]:
            # Use max rather than sum to avoid artificially high values
            results["overall_strength"] = max(c["strength"] for c in results["contradictions"])
        
        return results
