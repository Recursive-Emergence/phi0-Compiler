import numpy as np
from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session
import logging
from backend.models.database import Psi0Attractor, GridCell
from shapely import wkb
from shapely.geometry import Point, shape
from geoalchemy2.shape import to_shape, from_shape

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttractorFramework:
    """
    Implements the Symbolic Injection (ψ⁰ Attractor Placement) framework.
    
    This class manages the creation, placement, and influence calculation of
    ψ⁰ attractors that represent symbolic knowledge in the RE system.
    """
    
    def __init__(self, db_session: Session):
        """Initialize the attractor framework"""
        self.db = db_session
        
    def create_attractor(self, 
                        name: str, 
                        attractor_type: str, 
                        coordinates: Tuple[float, float],
                        strength: float,
                        influence_radius: float,
                        metadata: Dict[str, Any] = None) -> Psi0Attractor:
        """
        Create a new ψ⁰ attractor
        
        Args:
            name: Name of the attractor
            attractor_type: Type of attractor (hydrological, geological, symbolic, etc.)
            coordinates: (longitude, latitude) of the attractor
            strength: Strength of the attractor (0.0 to 1.0)
            influence_radius: Radius of influence in degrees
            metadata: Additional metadata for the attractor
            
        Returns:
            Created attractor entity
        """
        try:
            # Create point geometry
            point = Point(coordinates)
            
            # Create the attractor
            attractor = Psi0Attractor(
                attractor_name=name,
                attractor_type=attractor_type,
                strength=min(max(strength, 0.0), 1.0),  # Ensure in range [0, 1]
                influence_radius=influence_radius,
                geom=from_shape(point),
                symbolic_metadata=metadata or {}
            )
            
            self.db.add(attractor)
            self.db.commit()
            self.db.refresh(attractor)
            
            logger.info(f"Created attractor: {name} at {coordinates}")
            
            return attractor
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating attractor: {e}")
            raise
    
    def get_attractors(self, 
                      attractor_type: str = None, 
                      region_bbox: Tuple[float, float, float, float] = None) -> List[Dict[str, Any]]:
        """
        Get attractors, optionally filtered by type or region
        
        Args:
            attractor_type: Optional type to filter by
            region_bbox: Optional (min_lon, min_lat, max_lon, max_lat) to filter by region
            
        Returns:
            List of attractors with their properties
        """
        try:
            query = self.db.query(Psi0Attractor)
            
            if attractor_type:
                query = query.filter(Psi0Attractor.attractor_type == attractor_type)
            
            if region_bbox:
                min_lon, min_lat, max_lon, max_lat = region_bbox
                query = query.filter(
                    Psi0Attractor.geom.ST_X() >= min_lon,
                    Psi0Attractor.geom.ST_X() <= max_lon,
                    Psi0Attractor.geom.ST_Y() >= min_lat,
                    Psi0Attractor.geom.ST_Y() <= max_lat
                )
            
            result = []
            for attractor in query.all():
                geom = to_shape(attractor.geom)
                
                result.append({
                    "id": attractor.id,
                    "name": attractor.attractor_name,
                    "type": attractor.attractor_type,
                    "strength": attractor.strength,
                    "influence_radius": attractor.influence_radius,
                    "coordinates": (geom.x, geom.y),
                    "metadata": attractor.symbolic_metadata
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting attractors: {e}")
            return []
    
    def calculate_cell_influences(self, cell_id: str) -> Dict[str, Any]:
        """
        Calculate the influence of all attractors on a specific cell
        
        Args:
            cell_id: ID of the cell to calculate influences for
            
        Returns:
            Dictionary with influence details
        """
        try:
            # Get cell coordinates
            cell = self.db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
            if not cell:
                logger.error(f"Cell {cell_id} not found")
                return {"influences": [], "total_influence": 0.0}
            
            cell_centroid = to_shape(cell.centroid)
            
            # Get all attractors
            attractors = self.get_attractors()
            
            influences = []
            total_influence = 0.0
            
            for attractor in attractors:
                attractor_point = Point(attractor["coordinates"])
                distance = cell_centroid.distance(attractor_point)
                
                # Only consider attractors within their influence radius
                if distance <= attractor["influence_radius"]:
                    # Calculate decay based on distance (linear decay)
                    decay_factor = 1.0 - (distance / attractor["influence_radius"])
                    influence_strength = attractor["strength"] * decay_factor
                    
                    influences.append({
                        "attractor_id": attractor["id"],
                        "attractor_name": attractor["name"],
                        "attractor_type": attractor["type"],
                        "influence_strength": influence_strength,
                        "distance": distance
                    })
                    
                    total_influence += influence_strength
            
            # Cap total influence at 1.0
            total_influence = min(total_influence, 1.0)
            
            return {
                "cell_id": cell_id,
                "influences": influences,
                "total_influence": total_influence
            }
            
        except Exception as e:
            logger.error(f"Error calculating cell influences: {e}")
            return {"influences": [], "total_influence": 0.0}
    
    def generate_influence_field(self, region_bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Generate an influence field for all cells in a region
        
        Args:
            region_bbox: (min_lon, min_lat, max_lon, max_lat) to define the region
            
        Returns:
            Dictionary with influence field data
        """
        try:
            # Get all cells in the region
            min_lon, min_lat, max_lon, max_lat = region_bbox
            cells = self.db.query(GridCell).filter(
                GridCell.centroid.ST_X() >= min_lon,
                GridCell.centroid.ST_X() <= max_lon,
                GridCell.centroid.ST_Y() >= min_lat,
                GridCell.centroid.ST_Y() <= max_lat
            ).all()
            
            # Get all attractors in the region (plus buffer)
            buffer = max(max_lon - min_lon, max_lat - min_lat)
            region_with_buffer = (min_lon - buffer, min_lat - buffer, max_lon + buffer, max_lat + buffer)
            attractors = self.get_attractors(region_bbox=region_with_buffer)
            
            # Calculate influence for each cell
            influence_field = {
                "region": region_bbox,
                "cell_count": len(cells),
                "attractor_count": len(attractors),
                "field_data": {}
            }
            
            for cell in cells:
                cell_centroid = to_shape(cell.centroid)
                cell_influences = []
                total_influence = 0.0
                
                for attractor in attractors:
                    attractor_point = Point(attractor["coordinates"])
                    distance = cell_centroid.distance(attractor_point)
                    
                    if distance <= attractor["influence_radius"]:
                        decay_factor = 1.0 - (distance / attractor["influence_radius"])
                        influence_strength = attractor["strength"] * decay_factor
                        
                        cell_influences.append({
                            "attractor_id": attractor["id"],
                            "influence": influence_strength
                        })
                        
                        total_influence += influence_strength
                
                influence_field["field_data"][cell.cell_id] = {
                    "coordinates": (cell_centroid.x, cell_centroid.y),
                    "total_influence": min(total_influence, 1.0),
                    "attractors": cell_influences
                }
            
            return influence_field
            
        except Exception as e:
            logger.error(f"Error generating influence field: {e}")
            return {"region": region_bbox, "cell_count": 0, "attractor_count": 0, "field_data": {}}
    
    def create_symbolic_attractors(self, metadata_source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create symbolic attractors based on historical, mythological, or archaeological knowledge
        
        Args:
            metadata_source: Source information with coordinates and symbolic knowledge
            
        Returns:
            List of created attractors
        """
        # This is a simplified implementation of symbolic knowledge injection
        # In a real system, this would involve NLP, knowledge graph navigation, etc.
        
        created_attractors = []
        
        try:
            # Example: Create attractors for historical references
            if "historical_references" in metadata_source:
                for reference in metadata_source["historical_references"]:
                    if "coordinates" not in reference:
                        continue
                        
                    # Calculate strength based on source reliability and relevance
                    reliability = reference.get("reliability", 0.5)
                    relevance = reference.get("relevance", 0.5)
                    strength = (reliability + relevance) / 2.0
                    
                    # Create the attractor
                    attractor = self.create_attractor(
                        name=reference["name"],
                        attractor_type="historical",
                        coordinates=reference["coordinates"],
                        strength=strength,
                        influence_radius=reference.get("influence_radius", 0.1),
                        metadata={
                            "source": reference.get("source"),
                            "description": reference.get("description"),
                            "year": reference.get("year"),
                            "symbolism": reference.get("symbolism")
                        }
                    )
                    
                    created_attractors.append({
                        "id": attractor.id,
                        "name": attractor.attractor_name,
                        "type": attractor.attractor_type,
                        "strength": attractor.strength
                    })
            
            # Example: Create attractors for geological features
            if "geological_features" in metadata_source:
                for feature in metadata_source["geological_features"]:
                    if "coordinates" not in feature:
                        continue
                        
                    # Calculate strength based on feature importance
                    importance = feature.get("importance", 0.5)
                    anomaly_level = feature.get("anomaly_level", 0.5)
                    strength = (importance + anomaly_level) / 2.0
                    
                    # Create the attractor
                    attractor = self.create_attractor(
                        name=feature["name"],
                        attractor_type="geological",
                        coordinates=feature["coordinates"],
                        strength=strength,
                        influence_radius=feature.get("influence_radius", 0.05),
                        metadata={
                            "feature_type": feature.get("feature_type"),
                            "description": feature.get("description"),
                            "analysis": feature.get("analysis")
                        }
                    )
                    
                    created_attractors.append({
                        "id": attractor.id,
                        "name": attractor.attractor_name,
                        "type": attractor.attractor_type,
                        "strength": attractor.strength
                    })
            
            return created_attractors
            
        except Exception as e:
            logger.error(f"Error creating symbolic attractors: {e}")
            return []
