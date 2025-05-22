"""
NDVI Processor
=============
This module processes satellite imagery to extract NDVI (Normalized Difference Vegetation Index)
data for grid cells in the study area.
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

class NDVIProcessor:
    """
    Processes satellite imagery to extract NDVI data for archaeological analysis.
    
    NDVI is a key indicator for vegetation health and density, which can help
    identify anomalies that may indicate archaeological sites.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the NDVI processor
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.ee_connector = EarthEngineConnector()
        
        # Set default parameters
        self.sentinel2_collection = 'COPERNICUS/S2_SR'
        self.landsat8_collection = 'LANDSAT/LC08/C02/T1_L2'
        self.time_window_months = 24  # Use 2 years of data for stability
    
    def calculate_ndvi_for_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Calculate NDVI statistics for a specific grid cell
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with NDVI data (mean, std, etc.)
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
        
        # Get Sentinel-2 imagery
        try:
            s2_collection = self.ee_connector.get_image_collection(self.sentinel2_collection)
            if not s2_collection:
                raise Exception("Failed to get Sentinel-2 collection")
                
            # Filter by date and location
            s2_filtered = s2_collection.filterDate(start_date.strftime('%Y-%m-%d'), 
                                                  end_date.strftime('%Y-%m-%d')) \
                                      .filterBounds(ee_geom)
            
            # Cloud masking
            s2_filtered = self._apply_cloud_mask(s2_filtered)
            
            # Calculate NDVI
            s2_with_ndvi = s2_filtered.map(self._calculate_ndvi_sentinel2)
            
            # Reduce to get statistics
            ndvi_stats = s2_with_ndvi.select('NDVI') \
                                    .reduceRegion(
                                        reducer=ee.Reducer.mean().combine(
                                            reducer2=ee.Reducer.stdDev(),
                                            sharedInputs=True
                                        ),
                                        geometry=ee_geom,
                                        scale=10,
                                        maxPixels=1e9
                                    ).getInfo()
            
            # Get NDVI matrix for pattern analysis (simplified)
            ndvi_image = s2_with_ndvi.select('NDVI').mean()
            ndvi_matrix = self._get_ndvi_matrix(ndvi_image, ee_geom, 10, 10)
            
            return {
                "cell_id": cell_id,
                "ndvi_mean": ndvi_stats.get('NDVI_mean'),
                "ndvi_std": ndvi_stats.get('NDVI_stdDev'),
                "ndvi_matrix": ndvi_matrix.tolist() if ndvi_matrix is not None else None,
                "source": "sentinel2",
                "time_window": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating NDVI for cell {cell_id}: {e}")
            # Fall back to Landsat if Sentinel fails
            try:
                return self._calculate_ndvi_landsat(cell_id, ee_geom, start_date, end_date)
            except Exception as e2:
                logger.error(f"Landsat fallback also failed for {cell_id}: {e2}")
                return {"error": f"NDVI calculation failed: {str(e2)}"}
    
    def _calculate_ndvi_sentinel2(self, image: ee.Image) -> ee.Image:
        """Calculate NDVI from Sentinel-2 image"""
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    def _calculate_ndvi_landsat(self, 
                              cell_id: str, 
                              ee_geom: ee.Geometry, 
                              start_date: datetime, 
                              end_date: datetime) -> Dict[str, Any]:
        """Calculate NDVI using Landsat 8 as a fallback"""
        collection = self.ee_connector.get_image_collection(self.landsat8_collection)
        if not collection:
            return {"error": "Failed to get Landsat 8 collection"}
            
        # Filter by date and location
        filtered = collection.filterDate(start_date.strftime('%Y-%m-%d'), 
                                       end_date.strftime('%Y-%m-%d')) \
                           .filterBounds(ee_geom)
        
        # Apply cloud masking
        filtered = filtered.map(lambda img: img.updateMask(img.select('QA_PIXEL').bitwiseAnd(1 << 3).eq(0)))
        
        # Calculate NDVI
        with_ndvi = filtered.map(lambda img: 
            img.addBands(img.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')))
        
        # Reduce to get statistics
        ndvi_stats = with_ndvi.select('NDVI') \
                            .reduceRegion(
                                reducer=ee.Reducer.mean().combine(
                                    reducer2=ee.Reducer.stdDev(),
                                    sharedInputs=True
                                ),
                                geometry=ee_geom,
                                scale=30,
                                maxPixels=1e9
                            ).getInfo()
        
        # Get NDVI matrix (simplified)
        ndvi_image = with_ndvi.select('NDVI').mean()
        ndvi_matrix = self._get_ndvi_matrix(ndvi_image, ee_geom, 10, 10)
        
        return {
            "cell_id": cell_id,
            "ndvi_mean": ndvi_stats.get('NDVI_mean'),
            "ndvi_std": ndvi_stats.get('NDVI_stdDev'),
            "ndvi_matrix": ndvi_matrix.tolist() if ndvi_matrix is not None else None,
            "source": "landsat8",
            "time_window": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "processing_timestamp": datetime.now().isoformat()
        }
    
    def _apply_cloud_mask(self, collection: ee.ImageCollection) -> ee.ImageCollection:
        """Apply cloud masking to Sentinel-2 collection"""
        def mask_clouds(image):
            # Get SCL band and mask cloud pixels
            scl = image.select('SCL')
            mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return image.updateMask(mask)
            
        return collection.map(mask_clouds)
    
    def _get_ndvi_matrix(self, 
                       ndvi_image: ee.Image, 
                       region: ee.Geometry, 
                       rows: int, 
                       cols: int) -> Optional[np.ndarray]:
        """
        Get NDVI matrix for a region (used for pattern detection)
        
        Args:
            ndvi_image: Earth Engine image with NDVI band
            region: Region to sample
            rows: Number of rows in output matrix
            cols: Number of columns in output matrix
            
        Returns:
            NumPy array with NDVI values
        """
        try:
            # Sample points in grid
            points = ee.FeatureCollection.randomPoints(region, rows*cols)
            
            # Sample NDVI values at points
            samples = ndvi_image.sampleRegions(
                collection=points,
                scale=10,
                geometries=True
            ).getInfo()
            
            # Convert to matrix
            if 'features' in samples:
                values = [f['properties']['NDVI'] for f in samples['features'] if 'NDVI' in f['properties']]
                if len(values) >= rows*cols:
                    return np.array(values[:rows*cols]).reshape(rows, cols)
            
            return None
        except Exception as e:
            logger.error(f"Error getting NDVI matrix: {e}")
            return None
    
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
                ndvi_data = self.calculate_ndvi_for_cell(cell.cell_id)
                if "error" not in ndvi_data:
                    # Save to database
                    self._save_ndvi_to_database(ndvi_data)
                    results["processed"] += 1
                    results["cell_ids"].append(cell.cell_id)
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing cell {cell.cell_id}: {e}")
                results["failed"] += 1
        
        return results
    
    def _save_ndvi_to_database(self, ndvi_data: Dict[str, Any]) -> None:
        """Save NDVI data to database"""
        cell_id = ndvi_data["cell_id"]
        
        # Check if environmental data exists for this cell
        env_data = self.db.query(EnvironmentalData).filter(
            EnvironmentalData.cell_id == cell_id
        ).first()
        
        if env_data:
            # Update existing record
            env_data.ndvi_mean = ndvi_data["ndvi_mean"]
            env_data.ndvi_std = ndvi_data["ndvi_std"]
            if "raw_data" in env_data.__dict__ and env_data.raw_data:
                raw_data = env_data.raw_data.copy() if isinstance(env_data.raw_data, dict) else {}
                raw_data["ndvi"] = ndvi_data
                env_data.raw_data = raw_data
            else:
                env_data.raw_data = {"ndvi": ndvi_data}
        else:
            # Create new record
            env_data = EnvironmentalData(
                cell_id=cell_id,
                ndvi_mean=ndvi_data["ndvi_mean"],
                ndvi_std=ndvi_data["ndvi_std"],
                raw_data={"ndvi": ndvi_data}
            )
            self.db.add(env_data)
        
        self.db.commit()
