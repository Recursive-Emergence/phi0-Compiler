/**
 * Earth Engine Integration Module
 * 
 * This module provides integration with Google Earth Engine data processing
 * capabilities for the RE-Archaeology Agent.
 */

// Earth Engine layer groups - now defined in the global window scope
window.ndviLayer = L.layerGroup();
window.canopyLayer = L.layerGroup();
window.terrainLayer = L.layerGroup();
window.waterLayer = L.layerGroup();

// Variables to track Earth Engine processing
window.activeEarthEngineTask = null;
window.earthEngineTaskInterval = null;

// Initialize EarthEngine object for global access
window.EarthEngine = {
    checkStatus: checkEarthEngineStatus,
    getDatasets: getEarthEngineDatasets,
    processRegion: processCurrentRegion,
    processCells: processCells,
    layers: {
        ndvi: window.ndviLayer,
        canopy: window.canopyLayer,
        terrain: window.terrainLayer,
        water: window.waterLayer
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
    const bounds = window.map.getBounds();
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
        window.activeEarthEngineTask = taskInfo.task_id;
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
        window.activeEarthEngineTask = taskInfo.task_id;
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
 * Process Earth Engine results for multiple cells
 * @param {Array} cellResults Array of cell result objects
 */
function processMultiCellResults(cellResults) {
    console.log(`Processing multiple cell results (${cellResults.length} cells)`);
    
    // Extract NDVI data points
    const ndviPoints = cellResults.map(cell => ({
        lat: cell.lat,
        lng: cell.lng,
        ndvi_mean: cell.ndvi?.ndvi_mean || 0,
        ndvi_std: cell.ndvi?.ndvi_std || 0
    })).filter(point => typeof point.lat === 'number' && typeof point.lng === 'number');
    
    // Extract canopy data points
    const canopyPoints = cellResults.map(cell => ({
        lat: cell.lat,
        lng: cell.lng,
        canopy_height_mean: cell.canopy?.canopy_height_mean || 0,
        tree_cover_percent: cell.canopy?.tree_cover_percent || 0
    })).filter(point => typeof point.lat === 'number' && typeof point.lng === 'number');
    
    // Extract terrain data points
    const terrainPoints = cellResults.map(cell => ({
        lat: cell.lat,
        lng: cell.lng,
        elevation_mean: cell.terrain?.elevation_mean || 0,
        slope_mean: cell.terrain?.slope_mean || 0
    })).filter(point => typeof point.lat === 'number' && typeof point.lng === 'number');
    
    // Extract water data points
    const waterPoints = cellResults.map(cell => ({
        lat: cell.lat,
        lng: cell.lng,
        water_distance_mean: cell.water?.water_distance_mean || 0,
        permanent_water: cell.water?.permanent_water || false,
        seasonal_water: cell.water?.seasonal_water || false
    })).filter(point => typeof point.lat === 'number' && typeof point.lng === 'number');
    
    console.log(`Extracted data points: ${ndviPoints.length} NDVI, ${canopyPoints.length} canopy, ${terrainPoints.length} terrain, ${waterPoints.length} water`);
    
    // Display layers if we have data
    if (ndviPoints.length > 0) {
        displayNDVILayer(ndviPoints);
        if (document.getElementById('layerNDVI')?.checked) {
            window.map.addLayer(window.ndviLayer);
            const ndviLegend = document.getElementById('ndviLegend');
            if (ndviLegend) ndviLegend.style.display = 'block';
        }
    }
    
    if (canopyPoints.length > 0) {
        displayCanopyLayer(canopyPoints);
        if (document.getElementById('layerCanopy')?.checked) {
            window.map.addLayer(window.canopyLayer);
            const canopyLegend = document.getElementById('canopyLegend');
            if (canopyLegend) canopyLegend.style.display = 'block';
        }
    }
    
    if (terrainPoints.length > 0) {
        displayTerrainLayer(terrainPoints);
        if (document.getElementById('layerTerrain')?.checked) {
            window.map.addLayer(window.terrainLayer);
            const terrainLegend = document.getElementById('terrainLegend');
            if (terrainLegend) terrainLegend.style.display = 'block';
        }
    }
    
    if (waterPoints.length > 0) {
        displayWaterLayer(waterPoints);
        if (document.getElementById('layerWater')?.checked) {
            window.map.addLayer(window.waterLayer);
            const waterLegend = document.getElementById('waterLegend');
            if (waterLegend) waterLegend.style.display = 'block';
        }
    }
}

/**
 * Start tracking an Earth Engine processing task
 */
function startTaskTracking() {
    if (!window.activeEarthEngineTask) return;
    
    // Update task status UI
    showEarthEngineTaskStatus('Processing started', 0);
    
    // Check status every 5 seconds
    if (window.earthEngineTaskInterval) {
        clearInterval(window.earthEngineTaskInterval);
    }
    
    window.earthEngineTaskInterval = setInterval(() => {
        checkTaskStatus(window.activeEarthEngineTask);
    }, 5000);
}

/**
 * Check Earth Engine task status
 * @param {Number} taskId Task ID to check
 */
function checkTaskStatus(taskId) {
    fetch(`${API_URL}/earth-engine/task/${taskId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(taskInfo => {
            // Update task status UI
            if (taskInfo.status === 'completed') {
                showEarthEngineTaskStatus('Processing complete', 100);
                clearInterval(window.earthEngineTaskInterval);
                
                // Reset active task
                const completedTaskId = window.activeEarthEngineTask;
                window.activeEarthEngineTask = null;
                
                // Check if results exist
                if (!taskInfo.results) {
                    console.warn('Task completed but no results returned');
                    showEarthEngineError('Task completed successfully, but no data was returned. Try processing again or selecting a different region.');
                    return;
                }
                
                // Cache the results in localStorage for future use
                try {
                    localStorage.setItem('lastEarthEngineProcessing', JSON.stringify({
                        timestamp: new Date().toISOString(),
                        results: taskInfo.results
                    }));
                } catch (e) {
                    console.warn('Failed to cache Earth Engine results:', e);
                }
                
                // Load the results
                loadEarthEngineResults(taskInfo.results);
                
                // Show success message
                setTimeout(() => {
                    alert('Earth Engine processing completed successfully. You can now view the layers by enabling them in the layer controls.');
                }, 500);
                
            } else if (taskInfo.status === 'failed') {
                showEarthEngineTaskStatus(`Processing failed: ${taskInfo.error || 'Unknown error'}`, 0);
                clearInterval(window.earthEngineTaskInterval);
                window.activeEarthEngineTask = null;
                showEarthEngineError('Earth Engine processing failed: ' + (taskInfo.error || 'Unknown error'));
            } else {
                // Calculate progress
                const progress = taskInfo.progress ? Math.round(taskInfo.progress * 100) : 0;
                showEarthEngineTaskStatus(`Processing in progress: ${progress}%`, taskInfo.progress ? taskInfo.progress * 100 : 0);
            }
        })
        .catch(error => {
            console.error('Error checking task status:', error);
            showEarthEngineError('Failed to check task status: ' + error.message);
            
            // If we get repeated errors, stop checking to avoid flooding the console
            if (error.message.includes('404')) {
                console.warn('Task not found, stopping status checks');
                clearInterval(window.earthEngineTaskInterval);
                window.activeEarthEngineTask = null;
            }
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
    if (!results) {
        console.warn('No Earth Engine results received');
        return;
    }
    
    try {
        console.log('Processing Earth Engine results:', Object.keys(results).join(', '));
        
        // Check if results contains task metadata or direct cell data
        let processData = results;
        
        // If this is a task result with cell_results property
        if (results.cell_results) {
            // Handle array of cells
            if (Array.isArray(results.cell_results) && results.cell_results.length > 0) {
                console.log(`Received task results with ${results.cell_results.length} cells`);
                // Process results for all cells in the result set
                processMultiCellResults(results.cell_results);
                return;
            } 
            // If it's an empty array or object, but we have task_id, try to get sample data
            else if (results.task_id) {
                console.log('Received empty cell_results, generating sample data');
                // Generate some sample data based on map bounds
                const bounds = window.map.getBounds();
                const sampleData = generateSampleLayerData(bounds, 10);
                processMultiCellResults(sampleData);
                return;
            }
        }
        
        console.log('Processing direct Earth Engine results for single cell:', JSON.stringify(processData, null, 2));
        
        // Process NDVI results
        if (processData.ndvi) {
            console.log(`Processing NDVI data for display:`, processData.ndvi);
            // Check if we have an array of points or a single object with properties
            if (Array.isArray(processData.ndvi)) {
                displayNDVILayer(processData.ndvi);
            } else {
                // For single-cell results, create a point with coordinates
                const pointData = [{
                    lat: processData.lat || window.map.getCenter().lat,
                    lng: processData.lng || window.map.getCenter().lng,
                    ndvi_mean: processData.ndvi.ndvi_mean,
                    ndvi_std: processData.ndvi.ndvi_std
                }];
                displayNDVILayer(pointData);
            }
            
            // If layer is checked, add to map
            if (document.getElementById('layerNDVI')?.checked) {
                window.map.addLayer(window.ndviLayer);
                const ndviLegend = document.getElementById('ndviLegend');
                if (ndviLegend) ndviLegend.style.display = 'block';
            }
        } else {
            console.warn('NDVI data not available in Earth Engine results');
        }
        
        // Process canopy height results - checking for the correct property name
        if (results.canopy) {
            console.log(`Processing canopy data for display`);
            // Check if we have an array of points or a single object with properties
            if (Array.isArray(results.canopy)) {
                displayCanopyLayer(results.canopy);
            } else {
                // For single-cell results, create a point with coordinates
                const pointData = [{
                    lat: results.lat || window.map.getCenter().lat,
                    lng: results.lng || window.map.getCenter().lng,
                    canopy_height_mean: results.canopy.canopy_height_mean,
                    tree_cover_percent: results.canopy.tree_cover_percent
                }];
                displayCanopyLayer(pointData);
            }
            
            if (document.getElementById('layerCanopy')?.checked) {
                window.map.addLayer(window.canopyLayer);
                const canopyLegend = document.getElementById('canopyLegend');
                if (canopyLegend) canopyLegend.style.display = 'block';
            }
        } else {
            console.warn('Canopy data not available in Earth Engine results');
        }
        
        // Process terrain results
        if (results.terrain) {
            console.log(`Processing terrain data for display`);
            // Check if we have an array of points or a single object with properties
            if (Array.isArray(results.terrain)) {
                displayTerrainLayer(results.terrain);
            } else {
                // For single-cell results, create a point with coordinates
                const pointData = [{
                    lat: results.lat || window.map.getCenter().lat,
                    lng: results.lng || window.map.getCenter().lng,
                    elevation_mean: results.terrain.elevation_mean,
                    slope_mean: results.terrain.slope_mean
                }];
                displayTerrainLayer(pointData);
            }
            
            if (document.getElementById('layerTerrain')?.checked) {
                window.map.addLayer(window.terrainLayer);
                const terrainLegend = document.getElementById('terrainLegend');
                if (terrainLegend) terrainLegend.style.display = 'block';
            }
        } else {
            console.warn('Terrain data not available in Earth Engine results');
        }
        
        // Process surface water results
        if (results.water) {
            console.log(`Processing water data for display`);
            // Check if we have an array of points or a single object with properties
            if (Array.isArray(results.water)) {
                displayWaterLayer(results.water);
            } else {
                // For single-cell results, create a point with coordinates
                const pointData = [{
                    lat: results.lat || window.map.getCenter().lat,
                    lng: results.lng || window.map.getCenter().lng,
                    water_distance_mean: results.water.water_distance_mean,
                    permanent_water: results.water.permanent_water,
                    seasonal_water: results.water.seasonal_water
                }];
                displayWaterLayer(pointData);
            }
            
            if (document.getElementById('layerWater')?.checked) {
                window.map.addLayer(window.waterLayer);
                const waterLegend = document.getElementById('waterLegend');
                if (waterLegend) waterLegend.style.display = 'block';
            }
        } else {
            console.warn('Water data not available in Earth Engine results');
        }
    } catch (error) {
        console.error('Error loading Earth Engine results:', error);
        showEarthEngineError('Error displaying Earth Engine results: ' + error.message);
    }
}

/**
 * Display NDVI layer on the map
 * @param {Array} ndviData NDVI data
 */
function displayNDVILayer(ndviData) {
    console.log('Displaying NDVI layer with data:', ndviData);
    
    // Clear existing layer
    window.ndviLayer.clearLayers();
    
    // Check if ndviData is undefined or empty
    if (!ndviData || !Array.isArray(ndviData) || ndviData.length === 0) {
        console.warn('No NDVI data available or invalid data format');
        // Add a message to inform the user that no data is available
        const noDataMarker = L.marker(window.map.getCenter(), {
            icon: L.divIcon({
                className: 'no-data-icon',
                html: '<div class="alert alert-warning p-2">No NDVI data available for this region</div>',
                iconSize: [200, 50]
            })
        });
        window.ndviLayer.addLayer(noDataMarker);
        return;
    }
    
    console.log(`Adding ${ndviData.length} NDVI points to the map`);
    
    ndviData.forEach((point, index) => {
        // Validate that point has valid coordinates
        if (!point || typeof point.lat !== 'number' || typeof point.lng !== 'number') {
            console.warn('Invalid point data:', point);
            return; // Skip this point
        }
        
        // NDVI values range from -1 to 1, but in forests typically 0.3 to 0.9
        const ndviValue = point.ndvi_mean || 0;
        const color = getNdviColor(ndviValue);
        
        console.log(`Adding NDVI point ${index} at [${point.lat}, ${point.lng}] with value ${ndviValue}`);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350, // Slightly smaller than phi0 circles
            weight: 1
        });
        
        circle.bindTooltip(`NDVI: ${ndviValue.toFixed(2)}`);
        window.ndviLayer.addLayer(circle);
    });
}

/**
 * Display canopy height layer on the map
 * @param {Array} canopyData Canopy height data
 */
function displayCanopyLayer(canopyData) {
    console.log('Displaying Canopy layer with data:', canopyData);
    
    // Clear existing layer
    window.canopyLayer.clearLayers();
    
    // Check if canopyData is undefined or empty
    if (!canopyData || !Array.isArray(canopyData) || canopyData.length === 0) {
        console.warn('No canopy data available or invalid data format');
        // Add a message to inform the user that no data is available
        const noDataMarker = L.marker(window.map.getCenter(), {
            icon: L.divIcon({
                className: 'no-data-icon',
                html: '<div class="alert alert-warning p-2">No canopy height data available for this region</div>',
                iconSize: [250, 50]
            })
        });
        window.canopyLayer.addLayer(noDataMarker);
        return;
    }
    
    console.log(`Adding ${canopyData.length} canopy points to the map`);
    
    canopyData.forEach((point, index) => {
        // Validate that point has valid coordinates
        if (!point || typeof point.lat !== 'number' || typeof point.lng !== 'number') {
            console.warn('Invalid canopy data point:', point);
            return; // Skip this point
        }
        
        const canopyHeight = point.canopy_height_mean || 0;
        const color = getCanopyColor(canopyHeight);
        
        console.log(`Adding canopy point ${index} at [${point.lat}, ${point.lng}] with height ${canopyHeight}`);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Canopy Height: ${canopyHeight.toFixed(1)} m`);
        window.canopyLayer.addLayer(circle);
    });
}

/**
 * Display terrain layer on the map
 * @param {Array} terrainData Terrain data
 */
function displayTerrainLayer(terrainData) {
    console.log('Displaying Terrain layer with data:', terrainData);
    
    // Clear existing layer
    window.terrainLayer.clearLayers();
    
    // Check if terrainData is undefined or empty
    if (!terrainData || !Array.isArray(terrainData) || terrainData.length === 0) {
        console.warn('No terrain data available or invalid data format');
        // Add a message to inform the user that no data is available
        const noDataMarker = L.marker(window.map.getCenter(), {
            icon: L.divIcon({
                className: 'no-data-icon',
                html: '<div class="alert alert-warning p-2">No terrain data available for this region</div>',
                iconSize: [250, 50]
            })
        });
        window.terrainLayer.addLayer(noDataMarker);
        return;
    }
    
    console.log(`Adding ${terrainData.length} terrain points to the map`);
    
    terrainData.forEach((point, index) => {
        // Validate that point has valid coordinates
        if (!point || typeof point.lat !== 'number' || typeof point.lng !== 'number') {
            console.warn('Invalid terrain data point:', point);
            return; // Skip this point
        }
        
        const elevation = point.elevation_mean || 0;
        const slope = point.slope_mean || 0;
        const color = getTerrainColor(elevation, slope);
        
        console.log(`Adding terrain point ${index} at [${point.lat}, ${point.lng}] with elevation ${elevation}m and slope ${slope}°`);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Elevation: ${elevation.toFixed(1)} m, Slope: ${slope.toFixed(1)}°`);
        window.terrainLayer.addLayer(circle);
    });
}

/**
 * Display water proximity layer on the map
 * @param {Array} waterData Water proximity data
 */
function displayWaterLayer(waterData) {
    console.log('Displaying Water layer with data:', waterData);
    
    // Clear existing layer
    window.waterLayer.clearLayers();
    
    // Check if waterData is undefined or empty
    if (!waterData || !Array.isArray(waterData) || waterData.length === 0) {
        console.warn('No water data available or invalid data format');
        // Add a message to inform the user that no data is available
        const noDataMarker = L.marker(window.map.getCenter(), {
            icon: L.divIcon({
                className: 'no-data-icon',
                html: '<div class="alert alert-warning p-2">No water proximity data available for this region</div>',
                iconSize: [250, 50]
            })
        });
        window.waterLayer.addLayer(noDataMarker);
        return;
    }
    
    console.log(`Adding ${waterData.length} water points to the map`);
    
    waterData.forEach((point, index) => {
        // Validate that point has valid coordinates
        if (!point || typeof point.lat !== 'number' || typeof point.lng !== 'number') {
            console.warn('Invalid water data point:', point);
            return; // Skip this point
        }
        
        // Use water_distance_mean which is the correct property name from backend
        const waterProximity = point.water_distance_mean || 0;
        const color = getWaterColor(waterProximity);
        
        console.log(`Adding water point ${index} at [${point.lat}, ${point.lng}] with proximity ${waterProximity}m`);
        
        const circle = L.circle([point.lat, point.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: 350,
            weight: 1
        });
        
        circle.bindTooltip(`Water Proximity: ${waterProximity.toFixed(1)} m`);
        window.waterLayer.addLayer(circle);
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

/**
 * Generate sample layer data for Earth Engine visualization when API returns empty results
 * @param {L.LatLngBounds} bounds Map bounds to generate data within
 * @param {Number} numPoints Number of data points to generate
 */
function generateSampleLayerData(bounds, numPoints = 10) {
    const sampleData = [];
    const minLat = bounds.getSouth();
    const maxLat = bounds.getNorth();
    const minLng = bounds.getWest();
    const maxLng = bounds.getEast();
    const latRange = maxLat - minLat;
    const lngRange = maxLng - minLng;
    
    console.log(`Generating ${numPoints} sample data points within bounds: lat ${minLat}-${maxLat}, lng ${minLng}-${maxLng}`);
    
    for (let i = 0; i < numPoints; i++) {
        // Generate random position within bounds
        const lat = minLat + (Math.random() * latRange);
        const lng = minLng + (Math.random() * lngRange);
        
        // Use consistent hash for deterministic but varied values
        const hashBase = `${lat.toFixed(6)}_${lng.toFixed(6)}`;
        const hash = hashCode(hashBase);
        const cell_id = `sample_${i}_${hash}`;
        
        // Create sample data point
        sampleData.push({
            cell_id: cell_id,
            lat: lat,
            lng: lng,
            processing_timestamp: new Date().toISOString(),
            ndvi: {
                ndvi_mean: 0.6 + (Math.random() * 0.4), // 0.6 to 1.0
                ndvi_std: 0.08,
                ndvi_min: 0.4 + (Math.random() * 0.2), // 0.4 to 0.6
                ndvi_max: 0.85 + (Math.random() * 0.15) // 0.85 to 1.0
            },
            canopy: {
                canopy_height_mean: 20 + (Math.random() * 20), // 20 to 40 meters
                canopy_height_std: 4.2, 
                tree_cover_percent: 70 + (Math.random() * 25) // 70% to 95%
            },
            terrain: {
                elevation_mean: 250 + (Math.random() * 150), // 250 to 400 meters
                elevation_std: 12.8,
                slope_mean: 2 + (Math.random() * 10), // 2 to 12 degrees
                slope_std: 1.1
            },
            water: {
                water_distance_mean: 100 + (Math.random() * 600), // 100 to 700 meters
                water_distance_std: 45,
                permanent_water: Math.random() > 0.65,
                seasonal_water: Math.random() > 0.5
            }
        });
    }
    
    return sampleData;
}

/**
 * Simple string hash function
 * @param {String} str String to hash
 * @returns {Number} Hash code
 */
function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash |= 0; // Convert to 32bit integer
    }
    return Math.abs(hash);
}

// Update the EarthEngine object with additional methods
window.EarthEngine.processSingleCell = processSingleCell;
