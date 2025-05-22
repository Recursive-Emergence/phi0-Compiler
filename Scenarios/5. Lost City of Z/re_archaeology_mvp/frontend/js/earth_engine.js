/**
 * Earth Engine Integration Module
 * 
 * This module provides integration with Google Earth Engine data processing
 * capabilities for the RE-Archaeology Agent.
 */

// Earth Engine layer groups
const ndviLayer = L.layerGroup();
const canopyLayer = L.layerGroup();
const terrainLayer = L.layerGroup();
const waterLayer = L.layerGroup();

// Variables to track Earth Engine processing
let activeEarthEngineTask = null;
let earthEngineTaskInterval = null;

// Initialize EarthEngine object for global access
window.EarthEngine = {
    checkStatus: checkEarthEngineStatus,
    getDatasets: getEarthEngineDatasets,
    processRegion: processCurrentRegion,
    processCells: processCells,
    layers: {
        ndvi: ndviLayer,
        canopy: canopyLayer,
        terrain: terrainLayer,
        water: waterLayer
    }
};

/**
 * Check Earth Engine connection status
 * @returns {Promise} Promise that resolves with status info
 */
function checkEarthEngineStatus() {
    return fetch(`${API_URL}/earth-engine/status`)
        .then(response => response.json())
        .catch(error => {
            console.error('Error checking Earth Engine status:', error);
            return { status: 'error', message: 'Failed to connect to Earth Engine API' };
        });
}

/**
 * Get available Earth Engine datasets
 * @returns {Promise} Promise that resolves with dataset info
 */
function getEarthEngineDatasets() {
    return fetch(`${API_URL}/earth-engine/datasets`)
        .then(response => response.json())
        .catch(error => {
            console.error('Error getting Earth Engine datasets:', error);
            return { datasets: [] };
        });
}

/**
 * Process current map region with Earth Engine
 * @returns {Promise} Promise that resolves with task info
 */
function processCurrentRegion() {
    // Get current map bounds
    const bounds = map.getBounds();
    const request = {
        bounding_box: {
            min_lon: bounds.getWest(),
            min_lat: bounds.getSouth(),
            max_lon: bounds.getEast(),
            max_lat: bounds.getNorth()
        },
        data_sources: [
            "COPERNICUS/S2_SR",
            "LARSE/GEDI/GEDI04_A_002",
            "USGS/SRTMGL1_003",
            "JRC/GSW1_3/GlobalSurfaceWater"
        ],
        max_cells: 50  // Limit the number of cells to process for performance
    };

    return fetch(`${API_URL}/earth-engine/process-region`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
    })
    .then(response => response.json())
    .then(taskInfo => {
        // Start tracking the task
        activeEarthEngineTask = taskInfo.task_id;
        startTaskTracking();
        return taskInfo;
    })
    .catch(error => {
        console.error('Error processing region:', error);
        showEarthEngineError('Failed to start Earth Engine processing task');
        return null;
    });
}

/**
 * Process specific cells with Earth Engine
 * @param {Array} cellIds Array of cell IDs to process
 * @returns {Promise} Promise that resolves with task info
 */
function processCells(cellIds) {
    const request = {
        cell_ids: cellIds,
        data_sources: [
            "COPERNICUS/S2_SR",
            "LARSE/GEDI/GEDI04_A_002",
            "USGS/SRTMGL1_003",
            "JRC/GSW1_3/GlobalSurfaceWater"
        ]
    };

    return fetch(`${API_URL}/earth-engine/process-cells`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
    })
    .then(response => response.json())
    .then(taskInfo => {
        // Start tracking the task
        activeEarthEngineTask = taskInfo.task_id;
        startTaskTracking();
        return taskInfo;
    })
    .catch(error => {
        console.error('Error processing cells:', error);
        showEarthEngineError('Failed to start Earth Engine cell processing task');
        return null;
    });
}

/**
 * Process a single cell synchronously
 * @param {String} cellId Cell ID to process
 * @returns {Promise} Promise that resolves with cell results
 */
function processSingleCell(cellId) {
    return fetch(`${API_URL}/earth-engine/process-cell/${cellId}`)
        .then(response => response.json())
        .catch(error => {
            console.error(`Error processing cell ${cellId}:`, error);
            return null;
        });
}

/**
 * Start tracking an Earth Engine processing task
 */
function startTaskTracking() {
    if (!activeEarthEngineTask) return;
    
    // Update task status UI
    showEarthEngineTaskStatus('Processing started', 0);
    
    // Check status every 5 seconds
    if (earthEngineTaskInterval) {
        clearInterval(earthEngineTaskInterval);
    }
    
    earthEngineTaskInterval = setInterval(() => {
        checkTaskStatus(activeEarthEngineTask);
    }, 5000);
}

/**
 * Check Earth Engine task status
 * @param {Number} taskId Task ID to check
 */
function checkTaskStatus(taskId) {
    fetch(`${API_URL}/earth-engine/task/${taskId}`)
        .then(response => response.json())
        .then(taskInfo => {
            // Update task status UI
            if (taskInfo.status === 'completed') {
                showEarthEngineTaskStatus('Processing complete', 100);
                clearInterval(earthEngineTaskInterval);
                loadEarthEngineResults(taskInfo.results);
            } else if (taskInfo.status === 'failed') {
                showEarthEngineTaskStatus(`Processing failed: ${taskInfo.error}`, 0);
                clearInterval(earthEngineTaskInterval);
            } else {
                // Calculate progress
                const progress = taskInfo.progress ? Math.round(taskInfo.progress * 100) : 'unknown';
                showEarthEngineTaskStatus(`Processing in progress: ${progress}%`, taskInfo.progress ? taskInfo.progress * 100 : 0);
            }
        })
        .catch(error => {
            console.error('Error checking task status:', error);
            showEarthEngineError('Failed to check task status');
        });
}

/**
 * Show Earth Engine task status
 * @param {String} message Status message
 * @param {Number} progress Progress percentage (0-100)
 */
function showEarthEngineTaskStatus(message, progress) {
    // Create or update task status element
    let statusElement = document.getElementById('eeTaskStatus');
    
    if (!statusElement) {
        // Create new status element
        statusElement = document.createElement('div');
        statusElement.id = 'eeTaskStatus';
        statusElement.classList.add('earth-engine-status');
        document.body.appendChild(statusElement);
    }
    
    // Construct status HTML
    statusElement.innerHTML = `
        <div class="ee-status-header">
            <span>Earth Engine Task</span>
            <button class="btn-close" onclick="document.getElementById('eeTaskStatus').remove()"></button>
        </div>
        <div class="ee-status-body">
            <p>${message}</p>
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" style="width: ${progress}%" role="progressbar"></div>
            </div>
        </div>
    `;
    
    // Make sure it's visible
    statusElement.style.display = 'block';
}

/**
 * Show Earth Engine error message
 * @param {String} message Error message
 */
function showEarthEngineError(message) {
    // Create or update error element
    let errorElement = document.getElementById('eeErrorMessage');
    
    if (!errorElement) {
        // Create new error element
        errorElement = document.createElement('div');
        errorElement.id = 'eeErrorMessage';
        errorElement.classList.add('earth-engine-error');
        document.body.appendChild(errorElement);
    }
    
    // Set error message
    errorElement.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Earth Engine Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Make sure it's visible
    errorElement.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        if (errorElement.parentNode) {
            errorElement.remove();
        }
    }, 10000);
}

/**
 * Load Earth Engine processing results into map layers
 * @param {Object} results Processing results
 */
function loadEarthEngineResults(results) {
    if (!results) return;
    
    // Process NDVI results
    if (results.ndvi) {
        displayNDVILayer(results.ndvi);
    }
    
    // Process canopy height results
    if (results.canopy_height) {
        displayCanopyLayer(results.canopy_height);
    }
    
    // Process terrain results
    if (results.terrain) {
        displayTerrainLayer(results.terrain);
    }
    
    // Process surface water results
    if (results.water) {
        displayWaterLayer(results.water);
    }
}

/**
 * Display NDVI layer on the map
 * @param {Array} ndviData NDVI data
 */
function displayNDVILayer(ndviData) {
    // Clear existing layer
    ndviLayer.clearLayers();
    
    ndviData.forEach(point => {
        // NDVI values range from -1 to 1, but in forests typically 0.3 to 0.9
        const ndviValue = point.ndvi_mean || 0;
        const color = getNdviColor(ndviValue);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350, // Slightly smaller than phi0 circles
            weight: 1
        });
        
        circle.bindTooltip(`NDVI: ${ndviValue.toFixed(2)}`);
        ndviLayer.addLayer(circle);
    });
}

/**
 * Display canopy height layer on the map
 * @param {Array} canopyData Canopy height data
 */
function displayCanopyLayer(canopyData) {
    // Clear existing layer
    canopyLayer.clearLayers();
    
    canopyData.forEach(point => {
        const canopyHeight = point.canopy_height_mean || 0;
        const color = getCanopyColor(canopyHeight);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Canopy Height: ${canopyHeight.toFixed(1)} m`);
        canopyLayer.addLayer(circle);
    });
}

/**
 * Display terrain layer on the map
 * @param {Array} terrainData Terrain data
 */
function displayTerrainLayer(terrainData) {
    // Clear existing layer
    terrainLayer.clearLayers();
    
    terrainData.forEach(point => {
        const elevation = point.elevation_mean || 0;
        const slope = point.slope_mean || 0;
        const color = getTerrainColor(elevation, slope);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Elevation: ${elevation.toFixed(1)} m, Slope: ${slope.toFixed(1)}°`);
        terrainLayer.addLayer(circle);
    });
}

/**
 * Display water proximity layer on the map
 * @param {Array} waterData Water proximity data
 */
function displayWaterLayer(waterData) {
    // Clear existing layer
    waterLayer.clearLayers();
    
    waterData.forEach(point => {
        const waterProximity = point.water_proximity || 0;
        const color = getWaterColor(waterProximity);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Water Proximity: ${waterProximity.toFixed(1)} m`);
        waterLayer.addLayer(circle);
    });
}

/**
 * Get color based on NDVI value
 * @param {Number} ndvi NDVI value (-1 to 1)
 * @returns {String} Color in hex format
 */
function getNdviColor(ndvi) {
    if (ndvi < 0) return '#ffffff'; // Non-vegetation
    if (ndvi < 0.2) return '#eeeeee'; // Sparse vegetation
    if (ndvi < 0.4) return '#ccffcc'; // Light vegetation
    if (ndvi < 0.6) return '#77cc77'; // Moderate vegetation
    if (ndvi < 0.8) return '#33aa33'; // Dense vegetation
    return '#006600'; // Very dense vegetation
}

/**
 * Get color based on canopy height
 * @param {Number} height Canopy height in meters
 * @returns {String} Color in hex format
 */
function getCanopyColor(height) {
    if (height < 5) return '#ffffff'; // Very short or no canopy
    if (height < 10) return '#ccffcc'; // Short canopy
    if (height < 20) return '#77cc77'; // Medium canopy
    if (height < 30) return '#33aa33'; // Tall canopy
    return '#006600'; // Very tall canopy
}

/**
 * Get color based on terrain features
 * @param {Number} elevation Elevation in meters
 * @param {Number} slope Slope in degrees
 * @returns {String} Color in hex format
 */
function getTerrainColor(elevation, slope) {
    // First prioritize by slope
    if (slope > 30) return '#aa3333'; // Very steep
    if (slope > 20) return '#cc7777'; // Steep
    if (slope > 10) return '#ddaaaa'; // Moderate slope
    
    // Then by elevation
    if (elevation > 1000) return '#ccccff'; // High elevation
    if (elevation > 500) return '#aaaadd'; // Medium-high elevation
    if (elevation > 200) return '#8888bb'; // Medium elevation
    if (elevation > 100) return '#666699'; // Low-medium elevation
    return '#444477'; // Low elevation
}

/**
 * Get color based on water proximity
 * @param {Number} proximity Distance to water in meters
 * @returns {String} Color in hex format
 */
function getWaterColor(proximity) {
    if (proximity < 50) return '#0000ff'; // Very close to water
    if (proximity < 200) return '#4444ff'; // Close to water
    if (proximity < 500) return '#8888ff'; // Somewhat close to water
    if (proximity < 1000) return '#ccccff'; // Moderate distance from water
    return '#f0f0ff'; // Far from water
}

// Update the EarthEngine object with additional methods
window.EarthEngine.processSingleCell = processSingleCell;
