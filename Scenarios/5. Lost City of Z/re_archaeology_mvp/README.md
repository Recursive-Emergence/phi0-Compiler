# RE-Archaeology Agent MVP

This repository contains the Minimum Viable Product (MVP 0.1) i#### Option 1: Remote PostgreSQL Database (Google Cloud)

The application can connect to a remote PostgreSQL database hosted on Google Cloud:

1. Update the `DATABASE_URL` in your `.env` file with the actual password (obtained securely from your team):
   ```
   DATABASE_URL=postgresql://postgres:<PASSWORD>@34.59.159.217:5432/postgres
   ```

2. Test the connection to the remote database:
   ```bash
   # Using psql client (replace <PASSWORD> with actual password)
   psql "dbname=postgres user=postgres password=<PASSWORD> hostaddr=34.59.159.217"
   
   # Or via Python (replace <PASSWORD> with actual password)
   python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=\"<PASSWORD>\" host=34.59.159.217'); print('Connection successful!')"
   ```

   > **Note**: When using the password in terminal commands, be aware that it might be saved in your command history.
   > Consider using environment variables or connection strings stored in files with proper permissions instead.the RE-Archaeology Agent System, which leverages Recursive Emergence principles to identify potential archaeological sites in the Amazon basin.

## System Architecture

The RE-Archaeology Agent system is composed of:

1. **Core RE Engine** - Implementation of contradiction detection, resonance calculation, attractor framework, and agent self-model
2. **Data Pipeline** - Earth Engine integration, data extraction, and preprocessing
3. **Backend API** - FastAPI-based REST API for accessing and analyzing data
4. **Frontend** - Web interface with interactive mapping, Earth Engine visualization, and discussion system

### Earth Engine Integration

The system leverages Google Earth Engine for processing satellite imagery and extracting environmental data. This includes:

- NDVI calculation from Sentinel-2 and Landsat imagery
- Canopy height extraction from GEDI LiDAR data
- Terrain analysis including elevation, slope and aspects
- Water proximity and hydrological feature extraction

The Earth Engine data pipeline is designed for efficiency and robustness, with fallback mechanisms and batch processing capabilities.

#### Earth Engine Visualization

The frontend includes specialized visualization tools for Earth Engine data:

- Interactive layer controls for toggling NDVI, canopy height, terrain, and water proximity layers
- Color-coded legends explaining data interpretation
- On-demand processing of visible map regions
- Cell-specific Earth Engine analysis with detailed environmental metrics
- Processing task monitoring and status indicators

## Key Features

- **φ⁰ Resonance Calculation** - Core algorithm for identifying archaeological potential based on environmental contradictions
- **Earth Engine Integration** - Data extraction and visualization from multiple satellite sources
- **ψ⁰ Attractors Framework** - Detection of patterns that often correlate with archaeological sites
- **Interactive Map Interface** - Geographic visualization with multiple customizable layers
- **Remote Sensing Visualization** - Interactive display of NDVI, canopy height, terrain features, and water proximity
- **Epistemic Triangulation** - Cross-referencing multiple datasources for verification
- **Discussion System** - Collaborative interpretation of findings
- **Task Monitoring** - Real-time tracking of Earth Engine processing tasks
- **Cell-level Analysis** - Detailed environmental assessment of specific grid cells

## Prerequisites

- Docker and Docker Compose
- PostgreSQL with PostGIS (provided via Docker)
- Python 3.8+
- Earth Engine API access (for full functionality)

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd re_archaeology_mvp
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root with the following variables (copy from .env.example):

```
# Database Connection (choose one option)
# Option 1: Local database connection
DATABASE_URL=postgresql://re_archaeology:re_archaeology_pass@db:5432/re_archaeology_db

# Option 2: Remote database connection (replace <PASSWORD> with actual password)
# DATABASE_URL=postgresql://postgres:<PASSWORD>@34.59.159.217:5432/postgres

# Redis Connection
REDIS_URL=redis://redis:6379/0

# Earth Engine Authentication
# Choose authentication method: 'service_account' or 'application_default'
EE_AUTH_METHOD=service_account
EE_SERVICE_ACCOUNT=your-service-account-email@developer.gserviceaccount.com
EE_PRIVATE_KEY_FILE=/path/to/private-key.json
EE_PROJECT_ID=your-gcp-project-id
```

> **⚠️ SECURITY WARNING**: Never commit your `.env` file with real passwords to version control.
> The actual database password should be securely shared among team members through a 
> password manager or secure communication channel, not in documentation or code.

### 3. Configure Database Connection

#### Option 1: Remote PostgreSQL Database (Google Cloud)

The application can connect to a remote PostgreSQL database hosted on Google Cloud:

1. Update the `DATABASE_URL` in your `.env` file:
   ```
   DATABASE_URL=postgresql://postgres:zWb@tZi48v%0ML@34.59.159.217:5432/postgres
   ```

2. Test the connection to the remote database:
   ```bash
   # Using psql client
   psql "dbname=postgres user=postgres password=<PASSWORD> hostaddr=34.59.159.217"
   
   # Or via Python
   python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=\"<PASSWORD>\" host=34.59.159.217'); print('Connection successful!')"
   ```

3. Note: The remote PostgreSQL server is version 17.5, so ensure compatibility with your client tools.

#### Option 2: Local PostgreSQL Database (Docker)

If you prefer using a local database for development:

1. Update the `DATABASE_URL` in your `.env` file to use the local Docker database:
   ```
   DATABASE_URL=postgresql://re_archaeology:re_archaeology_pass@db:5432/re_archaeology_db
   ```

2. Make sure the PostgreSQL Docker container is running:
   ```bash
   docker-compose up -d db
   ```

### 4. Earth Engine Authentication

#### Option 1: Service Account (Recommended for Production)

1. Create a Google Cloud Platform service account with Earth Engine access
2. Generate a private key JSON file
3. Save it securely and reference it in your `.env` file

#### Option 2: Application Default Credentials

1. Install the Google Cloud SDK
2. Run `gcloud auth application-default login`
3. Set `EE_AUTH_METHOD=application_default` in your `.env` file

#### Testing Earth Engine Connection

Once you've set up authentication, test your Earth Engine connection:

```bash
# Test connection using environment variables
python tools/test_ee_connection.py

# Or specify credentials directly
python tools/test_ee_connection.py --service-account=your-account@developer.gserviceaccount.com --key-file=/path/to/key.json
```

### 5. Start the Docker Containers

```bash
docker-compose up -d
```

This will start:
- Redis for caching and pubsub
- The backend FastAPI application

The Docker Compose setup is designed to work with either the remote or local database:

#### Using the Remote Database
1. Make sure your `.env` file has the remote database URL:
   ```
   DATABASE_URL=postgresql://postgres:zWb@tZi48v%0ML@34.59.159.217:5432/postgres
   ```
2. Since we're using the remote database, you can skip starting the local PostgreSQL container:
   ```bash
   docker-compose up -d backend redis
   ```

#### Using the Local Database
1. Update your `.env` file to use the local database connection:
   ```
   DATABASE_URL=postgresql://re_archaeology:re_archaeology_pass@db:5432/re_archaeology_db
   ```
2. Start all containers, including the local PostgreSQL:
   ```bash
   docker-compose up -d
   ```

### 6. Creating Database Schema

For a fresh database installation, you'll need to initialize the schema in the PostgreSQL database:

```bash
# First connect to the running backend container
docker-compose exec backend bash

# Then run the database schema initialization script
python -m backend.models.init_db
```

> Note: When using the remote database, make sure you have the necessary permissions to create schemas and tables.

### 7. Access the Application

- The web interface is available at: http://localhost:8000/frontend/index.html
- The API documentation is available at: http://localhost:8000/docs

## Usage Guide

### 1. Exploring the Map

- Use the map controls to explore the analysis area
- Toggle different layers using the checkboxes in the top right
- Click on colored regions to see details about phi0 resonance scores and environmental data

### 2. Discussions

- Click on the "Discussions" tab to view existing discussions
- Create new discussions about specific areas or findings
- Reference map states in your discussions for better collaboration
- The RE agent will participate in discussions to provide analysis and insights

### 3. Sharing Map Views

- Click the "Share Map View" button to create a shareable URL
- The URL contains the exact map state (position, zoom, active layers)
- You can paste these URLs in discussions to reference specific findings

### 4. Using Earth Engine Data Processing

#### Using the Earth Engine Features in the Web Interface

1. **Viewing Earth Engine Layers**
   - Toggle the Earth Engine layers using the checkboxes in the map controls section
   - NDVI layer shows vegetation density
   - Canopy height layer shows forest structure
   - Terrain layer shows elevation and slope features
   - Water proximity layer shows distance to water bodies

2. **Processing New Regions**
   - Click the "Process Current Region" button to analyze the visible map area
   - Select datasets to use in the processing modal
   - Set the maximum number of cells to process
   - Monitor task progress in the status indicator

3. **Analyzing Individual Cells**
   - Click on any cell to view detailed information
   - If Earth Engine data isn't available, use the "Analyze with Earth Engine" button
   - Review the detailed Earth Engine metrics in the cell details panel

#### Earth Engine API Endpoints

The system also provides several API endpoints for programmatic access:

#### Check Earth Engine Status
```
GET /api/v1/earth-engine/status
```

#### Process a Region
```
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
```

#### Process Specific Cells
```
POST /api/v1/earth-engine/process-cells
{
  "cell_ids": ["cell-123", "cell-456"],
  "data_sources": ["ndvi", "canopy"]
}
```

#### Check Task Status
```
GET /api/v1/earth-engine/task/{task_id}
```

#### Process a Single Cell (Synchronous)
```
GET /api/v1/earth-engine/process-cell/{cell_id}
```

## Developer Guide

### Project Structure

```
re_archaeology_mvp/
├── backend/
│   ├── api/                # FastAPI application and endpoints
│   │   ├── main.py         # Main FastAPI application
│   │   ├── database.py     # Database connection
│   │   └── routers/        # API route handlers
│   ├── core/               # Core RE algorithms
│   │   ├── agent_self_model/
│   │   ├── attractor_framework/
│   │   ├── contradiction_detection/
│   │   └── resonance_calculation/
│   ├── data_processors/    # Data processing pipelines
│   │   └── earth_engine/   # Earth Engine integration
│   │       ├── connector.py      # Authentication and core EE functionality
│   │       ├── ndvi_processor.py # NDVI data extraction
│   │       ├── canopy_processor.py # Canopy height processing
│   │       ├── env_features_processor.py # Environmental features
│   │       └── pipeline.py # Processing orchestration
│   ├── models/             # Database models
│   └── utils/              # Utility functions and configuration
├── data/                   # Data storage
├── db/                     # Database initialization scripts
│   └── scripts/
├── frontend/               # Web interface
│   ├── components/
│   ├── services/
│   └── styles/
└── docker-compose.yml      # Docker Compose configuration
```

### Running Tests

```bash
docker-compose exec backend pytest
```

### Development Workflow

1. Make changes to the code
2. The API server will auto-reload due to the `--reload` flag
3. Refresh your browser to see frontend changes

### Earth Engine Command-Line Tool

The project includes a command-line tool for processing Earth Engine data outside of the web interface:

```bash
# Check Earth Engine connection status
python tools/ee_processor.py status

# Process all cells in a region
python tools/ee_processor.py process-region --bbox=-63.5,-10.2,-63.2,-9.8 --sources=ndvi,canopy,terrain,water --max-cells=50 --output=region_results.json

# Process specific cells
python tools/ee_processor.py process-cells --cell-ids=cell-123,cell-456 --sources=ndvi,canopy --output=cells_results.json
```

This tool is useful for initial data loading, testing, and manual processing tasks.

## License

[License information]
