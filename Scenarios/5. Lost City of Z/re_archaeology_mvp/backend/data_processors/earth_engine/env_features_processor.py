"""
Environmental Features Processor
==============================
This module processes various environmental data sources to extract
features like elevation, slope, and water proximity for grid cells.
"""

import ee
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, mapping, LineString
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from backend.data_processors.earth_engine.connector import EarthEngineConnector
from backend.models.database import GridCell, EnvironmentalData
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentalFeatureProcessor:
    """
    Processes various environmental data sources to extract features for archaeological analysis.
    
    This includes elevation, slope, aspect, water proximity, and other terrain features
    that might be relevant for archaeological site prediction.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the environmental features processor
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.ee_connector = EarthEngineConnector()
        
        # Set default parameters
        self.dem_dataset = 'USGS/SRTMGL1_003'  # 30m SRTM
        self.water_dataset = 'JRC/GSW1_3/GlobalSurfaceWater'
        
    def calculate_terrain_features(self, cell_id: str) -> Dict[str, Any]:
        """
        Calculate terrain features (elevation, slope) for a specific grid cell
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with terrain data
        """
        # Get cell geometry from database
        cell = self.db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
        if not cell:
            logger.error(f"Cell {cell_id} not found in database")
            return {"error": "Cell not found"}
            
        # Convert PostGIS geometry to shapely geometry
        cell_geom = gpd.GeoSeries.from_wkb([bytes(cell.geom.data)], crs="EPSG:4326")[0]
        
        # Create EE geometry
        coords = [[[p[0], p[1]] for p in list(cell_geom.exterior.coords)]]
        ee_geom = self.ee_connector.create_geometry(coords)
        
        try:
            # Get DEM data
            dem = ee.Image(self.dem_dataset)
            
            # Calculate slope
            slope = ee.Terrain.slope(dem)
            
            # Calculate aspect
            aspect = ee.Terrain.aspect(dem)
            
            # Get statistics
            terrain_stats = ee.Dictionary.combine(
                dem.reduceRegion(
                    reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
                    geometry=ee_geom,
                    scale=30,
                    maxPixels=1e9
                ),
                slope.reduceRegion(
                    reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
                    geometry=ee_geom,
                    scale=30,
                    maxPixels=1e9
                ),
                aspect.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=ee_geom,
                    scale=30,
                    maxPixels=1e9
                )
            ).getInfo()
            
            return {
                "cell_id": cell_id,
                "elevation_mean": terrain_stats.get('elevation_mean'),
                "elevation_std": terrain_stats.get('elevation_stdDev'),
                "slope_mean": terrain_stats.get('slope_mean'),
                "slope_std": terrain_stats.get('slope_stdDev'),
                "aspect_mean": terrain_stats.get('aspect'),
                "source": "srtm",
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating terrain features for cell {cell_id}: {e}")
            return {"error": f"Terrain feature calculation failed: {str(e)}"}
    
    def calculate_water_proximity(self, cell_id: str) -> Dict[str, Any]:
        """
        Calculate proximity to water features for a specific grid cell
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with water proximity data
        """
        # Get cell geometry from database
        cell = self.db.query(GridCell).filter(GridCell.cell_id == cell_id).first()
        if not cell:
            logger.error(f"Cell {cell_id} not found in database")
            return {"error": "Cell not found"}
            
        # Convert PostGIS geometry to shapely geometry
        cell_geom = gpd.GeoSeries.from_wkb([bytes(cell.geom.data)], crs="EPSG:4326")[0]
        
        # Create EE geometry for cell
        cell_coords = [[[p[0], p[1]] for p in list(cell_geom.exterior.coords)]]
        cell_ee_geom = self.ee_connector.create_geometry(cell_coords)
        
        # Create a larger buffer for water feature search
        buffer_distance = 0.05  # ~5km at equator
        buffer_coords = cell_geom.buffer(buffer_distance)
        buffer_ee_geom = self.ee_connector.create_geometry(
            [[[p[0], p[1]] for p in list(buffer_coords.exterior.coords)]]
        )
        
        try:
            # Get JRC water data - occurrence represents % of time water was present
            water_img = ee.Image(self.water_dataset).select('occurrence')
            
            # Create a binary water mask (areas where water occurs >25% of the time)
            water_mask = water_img.gt(25)
            
            # Compute distance to water
            distance = water_mask.fastDistanceTransform().multiply(ee.Image.pixelArea().sqrt())
            
            # Get distance statistics
            distance_stats = distance.reduceRegion(
                reducer=ee.Reducer.min().combine(reducer2=ee.Reducer.mean(), sharedInputs=True),
                geometry=cell_ee_geom,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            # Calculate water coverage percentage
            water_coverage = water_mask.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=cell_ee_geom,
                scale=30,
                maxPixels=1e9
            ).getInfo().get('occurrence', 0) * 100  # Convert to percentage
            
            return {
                "cell_id": cell_id,
                "water_proximity": distance_stats.get('distance_min'),  # Min distance to water in meters
                "water_mean_distance": distance_stats.get('distance_mean'),  # Mean distance to water
                "water_coverage_percent": water_coverage,
                "source": "jrc_gsw",
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating water proximity for cell {cell_id}: {e}")
            return {"error": f"Water proximity calculation failed: {str(e)}"}
    
    def process_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Process all environmental features for a cell
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with all environmental features
        """
        results = {
            "cell_id": cell_id,
            "features": {}
        }
        
        # Calculate terrain features
        terrain_data = self.calculate_terrain_features(cell_id)
        if "error" not in terrain_data:
            results["features"]["terrain"] = terrain_data
        else:
            results["features"]["terrain_error"] = terrain_data["error"]
        
        # Calculate water proximity
        water_data = self.calculate_water_proximity(cell_id)
        if "error" not in water_data:
            results["features"]["water"] = water_data
        else:
            results["features"]["water_error"] = water_data["error"]
        
        # Save to database
        if "terrain" in results["features"] or "water" in results["features"]:
            self._save_features_to_database(results)
            results["saved"] = True
        else:
            results["saved"] = False
            
        return results
        
    def process_region(self, 
                     bounding_box: List[float], 
                     max_cells: int = 100) -> Dict[str, Any]:
        """
        Process all cells in a region
        
        Args:
            bounding_box: [min_lon, min_lat, max_lon, max_lat]
            max_cells: Maximum number of cells to process
            
        Returns:
            Dictionary with processing results
        """
        # Query cells in the bounding box
        cells = self.db.query(GridCell).filter(
            GridCell.lon_min >= bounding_box[0],
            GridCell.lat_min >= bounding_box[1],
            GridCell.lon_max <= bounding_box[2],
            GridCell.lat_max <= bounding_box[3]
        ).limit(max_cells).all()
        
        results = {
            "processed": 0,
            "terrain_success": 0,
            "water_success": 0,
            "failed": 0,
            "cell_ids": []
        }
        
        for cell in cells:
            try:
                cell_results = self.process_cell(cell.cell_id)
                
                if "terrain" in cell_results["features"]:
                    results["terrain_success"] += 1
                
                if "water" in cell_results["features"]:
                    results["water_success"] += 1
                
                if cell_results["saved"]:
                    results["processed"] += 1
                    results["cell_ids"].append(cell.cell_id)
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing cell {cell.cell_id}: {e}")
                results["failed"] += 1
        
        return results
    
    def _save_features_to_database(self, results: Dict[str, Any]) -> None:
        """Save environmental features to database"""
        cell_id = results["cell_id"]
        features = results["features"]
        
        # Check if environmental data exists for this cell
        env_data = self.db.query(EnvironmentalData).filter(
            EnvironmentalData.cell_id == cell_id
        ).first()
        
        if env_data:
            # Update existing record
            if "terrain" in features:
                env_data.elevation_mean = features["terrain"]["elevation_mean"]
                env_data.elevation_std = features["terrain"]["elevation_std"]
                env_data.slope_mean = features["terrain"]["slope_mean"]
                env_data.slope_std = features["terrain"]["slope_std"]
                
            if "water" in features:
                env_data.water_proximity = features["water"]["water_proximity"]
                
            # Update raw data
            if "raw_data" in env_data.__dict__ and env_data.raw_data:
                raw_data = env_data.raw_data.copy() if isinstance(env_data.raw_data, dict) else {}
                if "terrain" in features:
                    raw_data["terrain"] = features["terrain"]
                if "water" in features:
                    raw_data["water"] = features["water"]
                env_data.raw_data = raw_data
            else:
                env_data.raw_data = features
        else:
            # Create new record
            env_data_dict = {
                "cell_id": cell_id,
                "raw_data": features
            }
            
            # Add individual fields
            if "terrain" in features:
                env_data_dict["elevation_mean"] = features["terrain"]["elevation_mean"]
                env_data_dict["elevation_std"] = features["terrain"]["elevation_std"]
                env_data_dict["slope_mean"] = features["terrain"]["slope_mean"]
                env_data_dict["slope_std"] = features["terrain"]["slope_std"]
                
            if "water" in features:
                env_data_dict["water_proximity"] = features["water"]["water_proximity"]
            
            env_data = EnvironmentalData(**env_data_dict)
            self.db.add(env_data)
        
        self.db.commit()
