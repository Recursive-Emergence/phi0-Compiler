"""
Earth Engine Connector
=====================
This module handles authentication and connection to the Google Earth Engine API,
providing a foundation for all Earth Engine-based data processing tasks.
"""

import os
import ee
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EarthEngineConnector:
    """
    Manages connections to the Google Earth Engine API and provides
    utility methods for common Earth Engine operations.
    """
    
    def __init__(self):
        """Initialize the Earth Engine connector and authenticate"""
        self.initialized = False
        try:
            self._initialize()
        except Exception as e:
            logger.error(f"Earth Engine initialization failed: {e}")
    
    def _initialize(self):
        """Initialize and authenticate with Earth Engine"""
        from backend.data_processors.earth_engine.auth import authenticate_earth_engine
        
        # Use the authentication helper
        if authenticate_earth_engine():
            self.initialized = True
            logger.info("Earth Engine initialized successfully")
        else:
            self.initialized = False
            logger.error("Earth Engine initialization failed")
    
    def check_connection(self) -> bool:
        """Check if the connection to Earth Engine is active"""
        if not self.initialized:
            return False
            
        try:
            # Simple test to see if Earth Engine is working
            info = ee.Number(1).getInfo()
            return info == 1
        except Exception as e:
            logger.error(f"Earth Engine connection test failed: {e}")
            return False
    
    def get_image_collection(self, collection_id: str) -> Optional[ee.ImageCollection]:
        """
        Get an Earth Engine image collection
        
        Args:
            collection_id: Earth Engine collection ID (e.g., 'COPERNICUS/S2')
            
        Returns:
            Earth Engine ImageCollection object or None if error
        """
        if not self.initialized:
            logger.error("Earth Engine not initialized")
            return None
            
        try:
            return ee.ImageCollection(collection_id)
        except Exception as e:
            logger.error(f"Failed to get collection {collection_id}: {e}")
            return None
    
    def get_feature_collection(self, collection_id: str) -> Optional[ee.FeatureCollection]:
        """
        Get an Earth Engine feature collection
        
        Args:
            collection_id: Earth Engine collection ID (e.g., 'TIGER/2018/Counties')
            
        Returns:
            Earth Engine FeatureCollection object or None if error
        """
        if not self.initialized:
            logger.error("Earth Engine not initialized")
            return None
            
        try:
            return ee.FeatureCollection(collection_id)
        except Exception as e:
            logger.error(f"Failed to get feature collection {collection_id}: {e}")
            return None
    
    def create_geometry(self, coords: List[List[float]]) -> ee.Geometry:
        """
        Create an Earth Engine geometry from coordinates
        
        Args:
            coords: List of [longitude, latitude] coordinates
            
        Returns:
            Earth Engine Geometry object
        """
        return ee.Geometry.Polygon(coords)
    
    def export_image(self, 
                     image: ee.Image, 
                     region: ee.Geometry, 
                     filename: str, 
                     scale: int = 30) -> ee.batch.Task:
        """
        Export an Earth Engine image to Google Drive
        
        Args:
            image: Earth Engine image to export
            region: Region to export
            filename: Output filename
            scale: Output resolution in meters
            
        Returns:
            Earth Engine export task
        """
        task = ee.batch.Export.image.toDrive(
            image=image,
            region=region,
            description=filename,
            folder='RE_Archaeology',
            fileNamePrefix=filename,
            scale=scale,
            maxPixels=1e9
        )
        task.start()
        return task
    
    def check_task_status(self, task: ee.batch.Task) -> str:
        """Check the status of an Earth Engine task"""
        return task.status()['state']
