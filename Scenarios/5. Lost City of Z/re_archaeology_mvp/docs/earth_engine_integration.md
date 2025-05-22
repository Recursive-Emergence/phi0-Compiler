# Earth Engine Integration for RE-Archaeology Agent

This document provides an overview of the Earth Engine integration in the RE-Archaeology Agent MVP 0.1, including architecture, capabilities, and usage instructions.

## Architecture Overview

The Earth Engine integration consists of several components:

1. **Authentication Module** (`auth.py`) - Handles Earth Engine authentication with support for both service account and application default credentials.

2. **Core Connector** (`connector.py`) - Provides a foundation for Earth Engine operations, including initialization, collection access, and utility methods.

3. **Data Processors**:
   - **NDVI Processor** (`ndvi_processor.py`) - Extracts vegetation indices from Sentinel-2 and Landsat imagery.
   - **Canopy Processor** (`canopy_processor.py`) - Processes GEDI LiDAR data for canopy height metrics.
   - **Environmental Features Processor** (`env_features_processor.py`) - Extracts terrain features and water proximity.

4. **Processing Pipeline** (`pipeline.py`) - Orchestrates the data extraction workflow, managing task execution and data persistence.

5. **REST API** (`routers/earth_engine.py`) - Provides endpoints for triggering and monitoring Earth Engine processing tasks.

6. **Frontend Integration**:
   - **Earth Engine Module** (`frontend/js/earth_engine.js`) - JavaScript interface to Earth Engine API endpoints.
   - **UI Components** (`frontend/js/earth_engine_ui.js`) - User interface components for Earth Engine features.
   - **Visualization** - Map layers for NDVI, canopy height, terrain features, and water proximity.
   - **Legends and Styling** (`frontend/css/earth_engine.css`) - Visual styling and legends for Earth Engine data.

7. **Command-line Tools**:
   - **EE Processor** (`tools/ee_processor.py`) - Command-line interface for Earth Engine data processing.
   - **Connection Test** (`tools/test_ee_connection.py`) - Simple tool to verify Earth Engine connectivity.
   - **Sample Region Test** (`tools/sample_region_test.py`) - Demonstration of complete analysis workflow.

## Data Sources

The integration leverages multiple Earth Engine datasets:

| Dataset | Description | Resolution | Used For |
|---------|-------------|------------|----------|
| Sentinel-2 (COPERNICUS/S2_SR) | Multispectral satellite imagery | 10m-60m | NDVI calculation |
| GEDI (LARSE/GEDI/GEDI04_A_002) | LiDAR-based forest structure | 25m | Canopy height |
| SRTM (USGS/SRTMGL1_003) | Global elevation data | 30m | Terrain analysis |
| Global Surface Water (JRC/GSW1_3) | Water occurrence and change | 30m | Water proximity |
| Landsat 8 (LANDSAT/LC08/C02/T1_L2) | Multispectral satellite imagery | 30m | Backup NDVI |

## Processing Pipeline

The Earth Engine integration follows this workflow:

1. **Authentication** - Securely connect to Earth Engine API.
2. **Region Selection** - Define grid cells or regions of interest.
3. **Data Extraction** - Retrieve and process multiple environmental layers.
4. **Persistence** - Store results in the PostGIS database.
5. **Contradiction Detection** - Analyze data for patterns that contradict natural formation.
6. **Resonance Calculation** - Convert contradictions into archaeological potential scores.

## Usage Instructions

### API Endpoints

```
# Check Earth Engine connection status
GET /api/v1/earth-engine/status

# Get information about Earth Engine datasets
GET /api/v1/earth-engine/datasets

# Process a region
POST /api/v1/earth-engine/process-region
{
  "bounding_box": {
    "min_lon": -63.5,
    "min_lat": -10.2,
    "max_lon": -63.2,
    "max_lat": -9.8
  },
  "data_sources": ["ndvi", "canopy", "terrain", "water"],
  "max_cells": 100
}

# Process specific cells
POST /api/v1/earth-engine/process-cells
{
  "cell_ids": ["cell-123", "cell-456"],
  "data_sources": ["ndvi", "canopy"]
}

# Check task status
GET /api/v1/earth-engine/task/{task_id}

# Process a single cell (synchronous)
GET /api/v1/earth-engine/process-cell/{cell_id}
```

### Command-line Tools

```bash
# Check Earth Engine connection status
python tools/ee_processor.py status

# Process all cells in a region
python tools/ee_processor.py process-region --bbox=-63.5,-10.2,-63.2,-9.8 --sources=ndvi,canopy,terrain,water --max-cells=50

# Process specific cells
python tools/ee_processor.py process-cells --cell-ids=cell-123,cell-456 --sources=ndvi,canopy

# Test Earth Engine connection
python tools/test_ee_connection.py

# Run sample region analysis
python tools/sample_region_test.py
```

## Authentication Options

### Service Account (Recommended for Production)

1. Create a service account in Google Cloud Console.
2. Grant Earth Engine access to the service account.
3. Download service account key as JSON.
4. Configure environment variables:
   ```
   EE_AUTH_METHOD=service_account
   EE_SERVICE_ACCOUNT=your-service-account@developer.gserviceaccount.com
   EE_PRIVATE_KEY_FILE=/path/to/key.json
   EE_PROJECT_ID=your-project-id
   ```

### Application Default Credentials (Simpler for Development)

1. Install Google Cloud SDK.
2. Run `gcloud auth application-default login`.
3. Configure environment variables:
   ```
   EE_AUTH_METHOD=application_default
   ```

## Performance Considerations

- Earth Engine operations are limited by API quotas; batch processing is recommended.
- Most processing is done on Google's servers, but results need to be downloaded.
- For areas with sparse GEDI data, fallback sources are used for canopy height.
- Cloud masking is applied to ensure high-quality imagery.
- Results are cached in Redis and the database to avoid redundant processing.

## Future Enhancements

1. **Advanced GEDI handling** - Better interpolation of sparse GEDI data.
2. **Temporal analysis** - Detect changes in environmental features over time.
3. **Custom indices** - Add specialized vegetation and soil indices.
4. **Atmospheric correction** - Improve radiometric calibration for better consistency.
5. **Multi-source fusion** - Integrate data from multiple satellite sensors.
6. **Dynamic resolution** - Adapt processing scale based on feature importance.

## Frontend Interface

The Earth Engine integration is accessible through the web interface with the following features:

### Layer Controls
- Toggle NDVI visualization
- Toggle Canopy height visualization
- Toggle Terrain features visualization
- Toggle Water proximity visualization

### Region Processing
- Click the "Process Current Region" button to analyze the visible map area with Earth Engine
- Select which datasets to use for processing
- Set the maximum number of cells to process

### Cell Analysis
- Click on individual cells to view their details
- For cells without Earth Engine data, use the "Analyze with Earth Engine" button
- View detailed Earth Engine metrics in the cell details panel

### Layer Legends
- Each Earth Engine layer has a corresponding legend explaining the color scale
- Legends only appear when their respective layer is active
