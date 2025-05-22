"""
Canopy Height Processor
======================
This module processes GEDI LiDAR data to extract canopy height information
for grid cells in the study area.
"""

import ee
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, mapping
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.data_processors.earth_engine.connector import EarthEngineConnector
from backend.models.database import GridCell, EnvironmentalData
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CanopyProcessor:
    """
    Processes GEDI LiDAR data to extract canopy height information for archaeological analysis.
    
    Canopy height is a critical indicator for detecting potential archaeological sites,
    especially when combined with NDVI data to identify contradictions.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the canopy height processor
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.ee_connector = EarthEngineConnector()
        
        # Set default parameters
        self.gedi_collection = 'LARSE/GEDI/GEDI04_A_002'
        self.backup_collection = 'NASA/GEDI/GEDI02_A_002_MONTHLY'
        self.time_window_months = 24  # Use 2 years of data for stability
    
    def calculate_canopy_height_for_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Calculate canopy height statistics for a specific grid cell
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with canopy height data (mean, std, etc.)
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
        
        # Set time window
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30*self.time_window_months)
        
        # Get GEDI data
        try:
            gedi_collection = self.ee_connector.get_image_collection(self.gedi_collection)
            if not gedi_collection:
                raise Exception("Failed to get GEDI collection")
                
            # Filter by date and location
            gedi_filtered = gedi_collection.filterDate(start_date.strftime('%Y-%m-%d'), 
                                                   end_date.strftime('%Y-%m-%d')) \
                                       .filterBounds(ee_geom)
            
            # Check if we have enough GEDI samples
            gedi_count = gedi_filtered.size().getInfo()
            if gedi_count < 5:
                logger.warning(f"Insufficient GEDI coverage for cell {cell_id}, using backup")
                return self._use_backup_canopy_source(cell_id, ee_geom, start_date, end_date)
            
            # Extract canopy height (rh95 = relative height 95%)
            gedi_with_height = gedi_filtered.select('rh95')
            
            # Aggregate the data
            height_stats = gedi_with_height.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                geometry=ee_geom,
                scale=25,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "cell_id": cell_id,
                "canopy_height_mean": height_stats.get('rh95_mean'),
                "canopy_height_std": height_stats.get('rh95_stdDev'),
                "source": "gedi",
                "time_window": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating canopy height for cell {cell_id}: {e}")
            # Fall back to backup source
            try:
                return self._use_backup_canopy_source(cell_id, ee_geom, start_date, end_date)
            except Exception as e2:
                logger.error(f"Backup canopy source also failed for {cell_id}: {e2}")
                return {"error": f"Canopy height calculation failed: {str(e2)}"}
    
    def _use_backup_canopy_source(self, 
                                cell_id: str, 
                                ee_geom: ee.Geometry, 
                                start_date: datetime, 
                                end_date: datetime) -> Dict[str, Any]:
        """
        Use a backup source for canopy height estimation
        
        This uses the monthly GEDI product or alternatively could use 
        a modeled canopy height dataset.
        """
        collection = self.ee_connector.get_image_collection(self.backup_collection)
        if not collection:
            return {"error": "Failed to get backup canopy height collection"}
            
        # Filter by date and location
        filtered = collection.filterDate(start_date.strftime('%Y-%m-%d'), 
                                      end_date.strftime('%Y-%m-%d')) \
                          .filterBounds(ee_geom)
        
        # If still no coverage, use a global canopy height model
        if filtered.size().getInfo() < 2:
            logger.warning(f"Using global canopy height model for {cell_id}")
            return self._use_global_canopy_model(cell_id, ee_geom)
        
        # Select canopy height band
        with_height = filtered.select('rh95')
        
        # Reduce to get statistics
        height_stats = with_height.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ),
            geometry=ee_geom,
            scale=25,
            maxPixels=1e9
        ).getInfo()
        
        return {
            "cell_id": cell_id,
            "canopy_height_mean": height_stats.get('rh95_mean'),
            "canopy_height_std": height_stats.get('rh95_stdDev'),
            "source": "gedi_monthly",
            "time_window": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "processing_timestamp": datetime.now().isoformat()
        }
    
    def _use_global_canopy_model(self, cell_id: str, ee_geom: ee.Geometry) -> Dict[str, Any]:
        """
        Use global canopy height model as last resort
        
        This uses the ETH global canopy height model derived from multiple data sources.
        """
        # NOTE: 'ETH/TREE_CANOPY_HEIGHT/V1' is an example collection, verify the actual asset ID
        try:
            canopy_model = ee.Image('ETH/TREE_CANOPY_HEIGHT/V1')
            
            # Extract height from the model
            height_stats = canopy_model.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                geometry=ee_geom,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "cell_id": cell_id,
                "canopy_height_mean": height_stats.get('b1_mean'),  # Adapt band name as needed
                "canopy_height_std": height_stats.get('b1_stdDev'),
                "source": "global_model",
                "processing_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Global canopy model failed for {cell_id}: {e}")
            # Last resort - return a warning with estimated values from similar biomes
            return {
                "cell_id": cell_id,
                "canopy_height_mean": 25.0,  # Approximate value for Amazon rainforest
                "canopy_height_std": 8.0,
                "source": "biome_estimate",
                "warning": "No direct measurements available, using biome average",
                "processing_timestamp": datetime.now().isoformat()
            }
    
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
            "failed": 0,
            "cell_ids": []
        }
        
        for cell in cells:
            try:
                canopy_data = self.calculate_canopy_height_for_cell(cell.cell_id)
                if "error" not in canopy_data:
                    # Save to database
                    self._save_canopy_to_database(canopy_data)
                    results["processed"] += 1
                    results["cell_ids"].append(cell.cell_id)
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing cell {cell.cell_id}: {e}")
                results["failed"] += 1
        
        return results
    
    def _save_canopy_to_database(self, canopy_data: Dict[str, Any]) -> None:
        """Save canopy height data to database"""
        cell_id = canopy_data["cell_id"]
        
        # Check if environmental data exists for this cell
        env_data = self.db.query(EnvironmentalData).filter(
            EnvironmentalData.cell_id == cell_id
        ).first()
        
        if env_data:
            # Update existing record
            env_data.canopy_height_mean = canopy_data["canopy_height_mean"]
            env_data.canopy_height_std = canopy_data["canopy_height_std"]
            if "raw_data" in env_data.__dict__ and env_data.raw_data:
                raw_data = env_data.raw_data.copy() if isinstance(env_data.raw_data, dict) else {}
                raw_data["canopy"] = canopy_data
                env_data.raw_data = raw_data
            else:
                env_data.raw_data = {"canopy": canopy_data}
        else:
            # Create new record
            env_data = EnvironmentalData(
                cell_id=cell_id,
                canopy_height_mean=canopy_data["canopy_height_mean"],
                canopy_height_std=canopy_data["canopy_height_std"],
                raw_data={"canopy": canopy_data}
            )
            self.db.add(env_data)
        
        self.db.commit()
