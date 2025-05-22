#!/usr/bin/env python
"""
Earth Engine Sample Region Test
==============================

This script demonstrates the use of Earth Engine for analyzing a sample region 
in the Amazon basin, combining multiple data sources to create a comprehensive
environmental dataset.

It serves as both a test case and an example of how the RE-Archaeology Agent
processes Earth Engine data.
"""

import os
import sys
import ee
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

# Add the parent directory to sys.path to allow importing from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_processors.earth_engine.connector import EarthEngineConnector

# Load environment variables
load_dotenv()

# Configure the base directory for saving files
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'earth_engine', 'samples')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample region in the Amazon basin (approximate location for the Lost City of Z search area)
# These coordinates can be adjusted based on specific research interest
SAMPLE_REGION = {
    "min_lon": -63.5,
    "min_lat": -10.2,
    "max_lon": -63.2,
    "max_lat": -9.8
}

def initialize_earth_engine():
    """Initialize Earth Engine using credentials from environment variables"""
    try:
        ee_connector = EarthEngineConnector()
        return ee_connector.initialized
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        return False

def create_sample_region_geometry():
    """Create an Earth Engine geometry for the sample region"""
    coords = [
        [SAMPLE_REGION["min_lon"], SAMPLE_REGION["min_lat"]],
        [SAMPLE_REGION["max_lon"], SAMPLE_REGION["min_lat"]],
        [SAMPLE_REGION["max_lon"], SAMPLE_REGION["max_lat"]],
        [SAMPLE_REGION["min_lon"], SAMPLE_REGION["max_lat"]],
        [SAMPLE_REGION["min_lon"], SAMPLE_REGION["min_lat"]]
    ]
    return ee.Geometry.Polygon([coords])

def get_sentinel2_composite(region_geometry, start_date, end_date):
    """Get a cloud-free Sentinel-2 composite for the specified time range"""
    # Load Sentinel-2 surface reflectance data
    s2 = ee.ImageCollection('COPERNICUS/S2_SR')
    
    # Filter by date and region
    s2_filtered = s2.filterDate(start_date, end_date).filterBounds(region_geometry)
    
    # Function to mask clouds using the SCL band
    def mask_clouds(image):
        # Get SCL band - values 3, 8, 9, and 10 are cloud, cloud shadow, or cirrus
        scl = image.select('SCL')
        mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        return image.updateMask(mask)
    
    # Apply cloud masking
    s2_masked = s2_filtered.map(mask_clouds)
    
    # Create median composite to remove remaining clouds and noise
    composite = s2_masked.median()
    
    return composite

def calculate_ndvi(image):
    """Calculate NDVI from a Sentinel-2 image"""
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return ndvi

def get_elevation_data(region_geometry):
    """Get elevation data from SRTM"""
    # Load SRTM Digital Elevation Data
    srtm = ee.Image('USGS/SRTMGL1_003')
    
    # Calculate slope
    elevation = srtm.select('elevation')
    slope = ee.Terrain.slope(elevation)
    
    return elevation, slope

def get_water_data(region_geometry):
    """Get water occurrence data from JRC Global Surface Water dataset"""
    # Load JRC Global Surface Water dataset
    gsw = ee.Image('JRC/GSW1_3/GlobalSurfaceWater')
    
    # Get water occurrence band (percentage of time water was detected)
    occurrence = gsw.select('occurrence')
    
    # Create a water mask (areas where water is present >25% of the time)
    water_mask = occurrence.gt(25)
    
    # Calculate distance to water
    distance = water_mask.fastDistanceTransform().multiply(ee.Image.pixelArea().sqrt())
    
    return occurrence, distance

def get_canopy_height(region_geometry):
    """Get canopy height data from GEDI"""
    try:
        # Load GEDI canopy height data
        # Note: This is a simplified approach - actual implementation should handle sparse GEDI data
        gedi = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002')
        
        # Get mean canopy height (rh95 - 95% relative height)
        canopy = gedi.select('rh95').mean()
        
        return canopy
    except Exception as e:
        print(f"Error getting GEDI data: {e}")
        # Fall back to a backup canopy height dataset
        try:
            # Try to use the ETH global canopy height model
            canopy = ee.Image('ETH/TREE_CANOPY_HEIGHT/V1')
            return canopy
        except:
            print("Failed to get canopy height data")
            return None

def create_sample_grid(region_geometry, grid_size=0.05):
    """Create a sample grid over the region"""
    # Get region bounds
    bounds = region_geometry.bounds().getInfo()['coordinates'][0]
    min_x = min(pt[0] for pt in bounds)
    min_y = min(pt[1] for pt in bounds)
    max_x = max(pt[0] for pt in bounds)
    max_y = max(pt[1] for pt in bounds)
    
    # Create grid cells
    cells = []
    for x in np.arange(min_x, max_x, grid_size):
        for y in np.arange(min_y, max_y, grid_size):
            cells.append({
                'id': f"cell-{x:.4f}-{y:.4f}",
                'coordinates': [
                    [x, y],
                    [x + grid_size, y],
                    [x + grid_size, y + grid_size],
                    [x, y + grid_size],
                    [x, y]
                ]
            })
    
    return cells

def analyze_sample_grid(region_geometry, cells, s2_composite, ndvi, elevation, slope, water_distance):
    """Analyze sample grid cells and collect data"""
    results = []
    
    for cell in cells:
        cell_geom = ee.Geometry.Polygon([cell['coordinates']])
        
        try:
            # Get statistics for this cell
            ndvi_stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
                geometry=cell_geom,
                scale=10
            ).getInfo()
            
            elev_stats = elevation.reduceRegion(
                reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
                geometry=cell_geom,
                scale=30
            ).getInfo()
            
            slope_stats = slope.reduceRegion(
                reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
                geometry=cell_geom,
                scale=30
            ).getInfo()
            
            water_stats = water_distance.reduceRegion(
                reducer=ee.Reducer.min().combine(reducer2=ee.Reducer.mean(), sharedInputs=True),
                geometry=cell_geom,
                scale=30
            ).getInfo()
            
            # Collect results
            cell_result = {
                'id': cell['id'],
                'coordinates': cell['coordinates'],
                'ndvi_mean': ndvi_stats.get('NDVI_mean'),
                'ndvi_std': ndvi_stats.get('NDVI_stdDev'),
                'elevation_mean': elev_stats.get('elevation_mean'),
                'elevation_std': elev_stats.get('elevation_stdDev'),
                'slope_mean': slope_stats.get('slope_mean'),
                'slope_std': slope_stats.get('slope_stdDev'),
                'water_distance_min': water_stats.get('distance_min'),
                'water_distance_mean': water_stats.get('distance_mean')
            }
            
            results.append(cell_result)
            
        except Exception as e:
            print(f"Error analyzing cell {cell['id']}: {e}")
    
    return results

def detect_contradictions(cell_data):
    """
    Simplified implementation of contradiction detection
    that mirrors the core RE engine implementation
    """
    contradictions = []
    
    # NDVI-Canopy height contradiction
    # Simplification: We use elevation as a proxy for canopy height
    if cell_data['ndvi_mean'] > 0.7 and cell_data['elevation_mean'] < 100:
        # High vegetation density but low "canopy"
        contradictions.append({
            'type': 'ndvi_elevation',
            'description': 'High NDVI but low elevation',
            'strength': cell_data['ndvi_mean'] * (1 - (cell_data['elevation_mean'] / 200))
        })
    
    # Water proximity contradiction
    if 50 < cell_data['water_distance_min'] < 500 and cell_data['elevation_mean'] > 100:
        # Ideal settlement location: close to water but elevated
        proximity_factor = 1.0 - (cell_data['water_distance_min'] / 500.0)
        elevation_factor = min(cell_data['elevation_mean'] / 200.0, 1.0)
        strength = proximity_factor * elevation_factor
        
        contradictions.append({
            'type': 'water_proximity',
            'description': 'Ideal settlement location near water but elevated',
            'strength': strength
        })
    
    # Calculate overall contradiction strength
    overall_strength = max([c['strength'] for c in contradictions]) if contradictions else 0.0
    
    return {
        'contradictions': contradictions,
        'overall_strength': overall_strength
    }

def visualize_results(results):
    """Create visualizations of the sample data"""
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Create a figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot NDVI
        scatter1 = axs[0, 0].scatter(
            [r['coordinates'][0][0] for r in results],
            [r['coordinates'][0][1] for r in results],
            c=[r['ndvi_mean'] for r in results], 
            cmap='RdYlGn', 
            s=100,
            alpha=0.7
        )
        axs[0, 0].set_title('NDVI Mean')
        fig.colorbar(scatter1, ax=axs[0, 0])
        
        # Plot elevation
        scatter2 = axs[0, 1].scatter(
            [r['coordinates'][0][0] for r in results],
            [r['coordinates'][0][1] for r in results],
            c=[r['elevation_mean'] for r in results], 
            cmap='terrain', 
            s=100,
            alpha=0.7
        )
        axs[0, 1].set_title('Elevation Mean (m)')
        fig.colorbar(scatter2, ax=axs[0, 1])
        
        # Plot water distance
        scatter3 = axs[1, 0].scatter(
            [r['coordinates'][0][0] for r in results],
            [r['coordinates'][0][1] for r in results],
            c=[r['water_distance_min'] for r in results], 
            cmap='Blues_r', 
            s=100,
            alpha=0.7
        )
        axs[1, 0].set_title('Distance to Water (m)')
        fig.colorbar(scatter3, ax=axs[1, 0])
        
        # Plot contradiction strengths
        contradiction_strengths = []
        for r in results:
            # Add contradiction detection
            contradictions = detect_contradictions(r)
            contradiction_strengths.append(contradictions['overall_strength'])
        
        scatter4 = axs[1, 1].scatter(
            [r['coordinates'][0][0] for r in results],
            [r['coordinates'][0][1] for r in results],
            c=contradiction_strengths, 
            cmap='hot', 
            s=100,
            alpha=0.7
        )
        axs[1, 1].set_title('Contradiction Strength (φ⁰ Score)')
        fig.colorbar(scatter4, ax=axs[1, 1])
        
        # Add overall title
        plt.suptitle('RE-Archaeology Sample Region Analysis', fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save the figure
        fig_path = os.path.join(OUTPUT_DIR, 'sample_region_analysis.png')
        plt.savefig(fig_path)
        print(f"Visualization saved to {fig_path}")
        
        return fig_path
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        return None

def main():
    """Main function to run the sample analysis"""
    print("RE-Archaeology Agent - Earth Engine Sample Region Test")
    print("=====================================================")
    
    # Initialize Earth Engine
    print("Initializing Earth Engine...")
    if not initialize_earth_engine():
        print("Failed to initialize Earth Engine. Exiting.")
        sys.exit(1)
    
    # Create sample region geometry
    print(f"Creating sample region geometry for area: {json.dumps(SAMPLE_REGION)}")
    region = create_sample_region_geometry()
    
    # Set time range (last 2 years)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    print(f"Using time range: {start_date} to {end_date}")
    
    # Get Sentinel-2 composite
    print("Creating cloud-free Sentinel-2 composite...")
    s2_composite = get_sentinel2_composite(region, start_date, end_date)
    
    # Calculate NDVI
    print("Calculating NDVI...")
    ndvi = calculate_ndvi(s2_composite)
    
    # Get elevation and slope
    print("Getting terrain data...")
    elevation, slope = get_elevation_data(region)
    
    # Get water data
    print("Getting water data...")
    water_occurrence, water_distance = get_water_data(region)
    
    # Create sample grid
    print("Creating sample grid...")
    grid_size = 0.01  # Approx 1km at equator
    cells = create_sample_grid(region, grid_size)
    print(f"Created {len(cells)} grid cells")
    
    # Analyze grid cells
    print("Analyzing grid cells...")
    results = analyze_sample_grid(region, cells, s2_composite, ndvi, elevation, slope, water_distance)
    
    # Save results to JSON
    results_path = os.path.join(OUTPUT_DIR, 'sample_region_results.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {results_path}")
    
    # Create visualizations
    print("Creating visualizations...")
    viz_path = visualize_results(results)
    
    if viz_path:
        print(f"Analysis complete! Visualization saved to: {viz_path}")
    else:
        print("Analysis complete, but visualization failed.")
    
if __name__ == '__main__':
    main()
