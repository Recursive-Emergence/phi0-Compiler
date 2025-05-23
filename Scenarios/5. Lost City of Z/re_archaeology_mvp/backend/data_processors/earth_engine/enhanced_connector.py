"""
High Resolution Earth Engine Connector
====================================
Enhanced Earth Engine connector with 500m resolution grid cells
and advanced 7D attractor dimensions based on the research notebook.
"""

import os
import logging
import json
import ee
import numpy as np
from datetime import datetime
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
from skimage.measure import shannon_entropy

from backend.data_processors.earth_engine.auth import authenticate_earth_engine
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedEarthEngineConnector:
    """
    Enhanced Earth Engine connector with high-resolution (500m) grid cells
    and advanced 7D attractor dimensions based on the latest research.
    
    Improvements:
    - 0.005° resolution (~500m) instead of 0.05° (~5km)
    - Additional dimensions: NDBI, FractalNDVI, Curvature, ElevationAnomaly
    - Optimized buffer sizes for feature extraction
    - Improved temporal analysis for NDVI stability
    """
    
    def __init__(self, use_high_resolution=True):
        """Initialize the enhanced Earth Engine connector."""
        self.initialized = False
        self.use_high_resolution = use_high_resolution
        self.config_file = os.path.join(os.path.dirname(__file__), "config", "high_resolution_settings.json")
        
        # Try to load the high-resolution configuration
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                    logger.info("Loaded high-resolution Earth Engine configuration")
            else:
                # Fall back to default configuration
                self.config = self._get_default_config()
                logger.warning("High-resolution configuration not found, using default settings")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = self._get_default_config()
        
        # Initialize Earth Engine
        try:
            self.initialized = authenticate_earth_engine()
            if self.initialized:
                logger.info("Earth Engine initialized successfully with enhanced connector")
            else:
                logger.error("Failed to initialize Earth Engine")
        except Exception as e:
            logger.error(f"Error initializing Earth Engine: {e}")
    
    def _get_default_config(self):
        """Get default configuration if high-resolution config is not available."""
        return {
            "grid_resolution": {"degrees": 0.005},  # ~500m resolution
            "buffer_sizes": {
                "ndvi": 250,
                "ndbi": 250,
                "rh100": 25,
                "slope": 250,
                "curvature": 250,
                "elevation": {"local": 25, "context": 1000}
            }
        }
    
    def get_ndvi(self, lat, lon):
        """
        Get Normalized Difference Vegetation Index (NDVI) for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            NDVI value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["ndvi"]
            
            img = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
                .filterBounds(point)\
                .filterDate("2023-01-01", "2023-12-31")\
                .median()\
                .normalizedDifference(["B8", "B4"])
            
            val = img.reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                10
            ).get("nd")
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting NDVI: {e}")
            return None
    
    def get_ndbi(self, lat, lon):
        """
        Get Normalized Difference Built-up Index (NDBI) for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            NDBI value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
            
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["ndbi"]
            
            img = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
                .filterBounds(point)\
                .filterDate("2023-01-01", "2023-12-31")\
                .median()
                
            ndbi = img.normalizedDifference(["B11", "B8"])
            val = ndbi.reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                10
            ).get("nd")
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting NDBI: {e}")
            return None
    
    def get_rh100(self, lat, lon):
        """
        Get canopy height (RH100) for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            RH100 value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["rh100"]
            
            img = ee.ImageCollection("LARSE/GEDI/GEDI02_A_002_MONTHLY")\
                .filterBounds(point)\
                .filterDate("2023-01-01", "2023-12-31")\
                .median()
            
            val = img.select("rh100").reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                30
            ).get("rh100")
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting RH100: {e}")
            return None
    
    def get_slope(self, lat, lon):
        """
        Get terrain slope for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Slope value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["slope"]
            
            slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
            val = slope.reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                30
            ).get("slope")
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting slope: {e}")
            return None
    
    def get_curvature(self, lat, lon):
        """
        Get terrain curvature for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Curvature value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["curvature"]
            
            dem = ee.Image("USGS/SRTMGL1_003")
            slope = ee.Terrain.slope(dem)
            aspect = ee.Terrain.aspect(dem)
            curvature = slope.gradient().pow(2).add(aspect.gradient().pow(2)).sqrt()
            
            val = curvature.reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                30
            ).values().get(0)
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting curvature: {e}")
            return None
    
    def get_elevation_anomaly(self, lat, lon):
        """
        Get elevation anomaly (local vs. contextual) for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Elevation anomaly value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            local_buffer = self.config["buffer_sizes"]["elevation"]["local"]
            context_buffer = self.config["buffer_sizes"]["elevation"]["context"]
            
            dem = ee.Image("USGS/SRTMGL1_003")
            local = dem.reduceRegion(ee.Reducer.mean(), point.buffer(local_buffer), 30).get("elevation")
            context = dem.reduceRegion(ee.Reducer.mean(), point.buffer(context_buffer), 30).get("elevation")
            
            # Return the anomaly (difference between local and context elevation)
            return local.getInfo() - context.getInfo()
        except Exception as e:
            logger.error(f"Error extracting elevation anomaly: {e}")
            return None
    
    def get_ndvi_entropy(self, lat, lon):
        """
        Get NDVI entropy (standard deviation) for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            NDVI entropy value or None if extraction fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["ndvi"]
            
            collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
                .filterBounds(point)\
                .filterDate("2023-01-01", "2023-12-31")\
                .map(lambda img: img.normalizedDifference(["B8", "B4"]))
                
            std_dev = collection.reduce(ee.Reducer.stdDev())
            val = std_dev.reduceRegion(
                ee.Reducer.mean(), 
                point.buffer(buffer_size), 
                10
            ).get("nd")
            
            return val.getInfo()
        except Exception as e:
            logger.error(f"Error extracting NDVI entropy: {e}")
            return None
    
    def compute_fractal_ndvi(self, lat, lon):
        """
        Compute fractal NDVI (temporal ecological stability) for a location.
        
        This uses the Savitzky-Golay filter method from the notebook to calculate
        temporal stability of vegetation patterns.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Fractal NDVI value or None if computation fails
        """
        try:
            if not self.initialized:
                logger.error("Earth Engine not initialized")
                return None
                
            point = ee.Geometry.Point([lon, lat])
            buffer_size = self.config["buffer_sizes"]["ndvi"]
            
            # Get NDVI time series from 2018-2023
            ts = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
                .filterBounds(point)\
                .filterDate("2018-01-01", "2023-12-31")\
                .map(lambda img: img.normalizedDifference(["B8", "B4"]).rename("ndvi"))\
                .select("ndvi")\
                .sort("system:time_start")
            
            # Convert to Python list
            series = ts.aggregate_array("ndvi").getInfo()
            
            # Skip if not enough data points
            if len(series) < 10:
                return None
                
            # Apply Savitzky-Golay filter to smooth the time series
            series = savgol_filter(series, 5, 2)
            
            # Create time array for linear regression
            time = np.arange(len(series)).reshape(-1, 1)
            
            # Fit linear model to remove trend
            model = LinearRegression().fit(time, series)
            
            # Calculate residuals
            residuals = series - model.predict(time)
            
            # Calculate Shannon entropy of residuals (measures complexity/stability)
            entropy = shannon_entropy(residuals)
            
            return entropy
        except Exception as e:
            logger.error(f"Error computing fractal NDVI: {e}")
            return None
    
    def extract_all_features(self, lat, lon):
        """
        Extract all 7D attractor dimensions for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with all extracted features
        """
        features = {
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.utcnow().isoformat(),
            "features": {}
        }
        
        # Extract each feature
        features["features"]["NDVI"] = self.get_ndvi(lat, lon)
        features["features"]["NDBI"] = self.get_ndbi(lat, lon)
        features["features"]["RH100"] = self.get_rh100(lat, lon)
        features["features"]["Slope"] = self.get_slope(lat, lon)
        features["features"]["Curvature"] = self.get_curvature(lat, lon)
        features["features"]["ElevationAnomaly"] = self.get_elevation_anomaly(lat, lon)
        features["features"]["NDVI_Entropy"] = self.get_ndvi_entropy(lat, lon)
        features["features"]["FractalNDVI"] = self.compute_fractal_ndvi(lat, lon)
        
        # Count how many features were successfully extracted
        success_count = sum(1 for val in features["features"].values() if val is not None)
        features["success_ratio"] = success_count / len(features["features"])
        
        return features
    
    def create_grid(self, min_lat, min_lon, max_lat, max_lon, resolution=None):
        """
        Create a grid of points within a bounding box.
        
        Args:
            min_lat: Minimum latitude
            min_lon: Minimum longitude
            max_lat: Maximum latitude
            max_lon: Maximum longitude
            resolution: Grid resolution in degrees (default: from config)
            
        Returns:
            List of (lat, lon) pairs
        """
        if resolution is None:
            resolution = self.config["grid_resolution"]["degrees"]
            
        grid_points = []
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                grid_points.append((lat, lon))
                lon += resolution
            lat += resolution
        
        return grid_points
