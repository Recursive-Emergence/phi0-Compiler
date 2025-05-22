// Earth Engine Toggle Layer function
function toggleEarthEngineLayer(e) {
    const layerId = e.target.id;
    const checked = e.target.checked;
    
    // Hide all Earth Engine legends first
    const ndviLegend = document.getElementById('ndviLegend');
    const canopyLegend = document.getElementById('canopyLegend');
    const terrainLegend = document.getElementById('terrainLegend');
    const waterLegend = document.getElementById('waterLegend');
    
    if (ndviLegend) ndviLegend.style.display = 'none';
    if (canopyLegend) canopyLegend.style.display = 'none';
    if (terrainLegend) terrainLegend.style.display = 'none';
    if (waterLegend) waterLegend.style.display = 'none';
    
    // Ensure EarthEngine object exists
    if (!window.EarthEngine || !window.EarthEngine.layers) {
        console.error('Earth Engine not initialized properly');
        return;
    }
    
    if (layerId === 'layerNDVI') {
        if (checked) {
            if (EarthEngine.layers.ndvi.getLayers().length === 0) {
                // Check if we need to process data first
                processEarthEngineLayerData('ndvi');
            }
            map.addLayer(EarthEngine.layers.ndvi);
            if (ndviLegend) ndviLegend.style.display = 'block';
        } else {
            map.removeLayer(EarthEngine.layers.ndvi);
        }
    } else if (layerId === 'layerCanopy') {
        if (checked) {
            if (EarthEngine.layers.canopy.getLayers().length === 0) {
                processEarthEngineLayerData('canopy');
            }
            map.addLayer(EarthEngine.layers.canopy);
            if (canopyLegend) canopyLegend.style.display = 'block';
        } else {
            map.removeLayer(EarthEngine.layers.canopy);
        }
    } else if (layerId === 'layerTerrain') {
        if (checked) {
            if (EarthEngine.layers.terrain.getLayers().length === 0) {
                processEarthEngineLayerData('terrain');
            }
            map.addLayer(EarthEngine.layers.terrain);
            if (terrainLegend) terrainLegend.style.display = 'block';
        } else {
            map.removeLayer(EarthEngine.layers.terrain);
        }
    } else if (layerId === 'layerWater') {
        if (checked) {
            if (EarthEngine.layers.water.getLayers().length === 0) {
                processEarthEngineLayerData('water');
            }
            map.addLayer(EarthEngine.layers.water);
            if (waterLegend) waterLegend.style.display = 'block';
        } else {
            map.removeLayer(EarthEngine.layers.water);
        }
    }
}

// Process Earth Engine data for a specific layer
function processEarthEngineLayerData(layerType) {
    // Check if we have any processed data
    // If not, prompt user to process the current region
    if (confirm('No Earth Engine data available for this layer. Would you like to process the current map region?')) {
        openProcessRegionModal();
    }
}

// Open process region modal
function openProcessRegionModal() {
    // Check Earth Engine connection first
    EarthEngine.checkStatus().then(status => {
        if (status.status === 'error' || status.status === 'failed') {
            // Display error message
            showEarthEngineError(`Earth Engine connection failed: ${status.message}`);
            return;
        }
        
        // Proceed with showing modal
        createProcessRegionModal();
        const modal = new bootstrap.Modal(document.getElementById('processRegionModal'));
        modal.show();
        
        // Load available datasets
        EarthEngine.getDatasets().then(response => {
            if (!response.datasets || response.datasets.length === 0) {
                document.getElementById('datasetsContainer').innerHTML = '<div class="alert alert-warning">No datasets available</div>';
                return;
            }
            
            const datasetsHtml = response.datasets.map(dataset => `
                <div class="dataset-item">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="dataset-${dataset.id.replace(/\//g, '-')}" checked>
                        <label class="form-check-label" for="dataset-${dataset.id.replace(/\//g, '-')}">
                            <strong>${dataset.name}</strong>
                        </label>
                    </div>
                    <div class="small text-muted">${dataset.description}</div>
                    <div class="small">Resolution: ${dataset.resolution} | Coverage: ${dataset.temporal_coverage}</div>
                </div>
            `).join('');
            
            document.getElementById('datasetsContainer').innerHTML = datasetsHtml;
        });
    });
}

// Create the process region modal
function createProcessRegionModal() {
    // Check if modal already exists
    if (document.getElementById('processRegionModal')) {
        return;
    }
    
    // Create modal element
    const modalElement = document.createElement('div');
    modalElement.id = 'processRegionModal';
    modalElement.className = 'modal fade';
    modalElement.tabIndex = '-1';
    
    modalElement.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header region-processing-header">
                    <h5 class="modal-title">Process Region with Earth Engine</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>
                        This will process the current map region with Google Earth Engine to extract environmental
                        features useful for archaeological site detection. This may take several minutes depending on
                        the region size and selected datasets.
                    </p>
                    
                    <div class="mb-3">
                        <label class="form-label">Current Map Bounds:</label>
                        <div id="boundingBoxCoords" class="form-control bg-light"></div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Maximum Cells to Process:</label>
                        <input type="number" class="form-control" id="maxCellsInput" value="50" min="1" max="500">
                        <div class="form-text">Higher values will provide more detailed results but take longer to process.</div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Datasets to Process:</label>
                        <div id="datasetsContainer" class="datasets-container">
                            <div class="d-flex justify-content-center">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-success" id="startProcessingBtn">Start Processing</button>
                </div>
            </div>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(modalElement);
    
    // Update bounding box coordinates
    const bounds = map.getBounds();
    document.getElementById('boundingBoxCoords').textContent = `
        North: ${bounds.getNorth().toFixed(6)}, South: ${bounds.getSouth().toFixed(6)},
        East: ${bounds.getEast().toFixed(6)}, West: ${bounds.getWest().toFixed(6)}
    `;
    
    // Wire up start processing button
    document.getElementById('startProcessingBtn').addEventListener('click', startRegionProcessing);
}

// Legends are now included directly in the HTML, so we don't need to load them dynamically
function loadEarthEngineLegends() {
    // Legends are now included directly in the HTML
    // Just make sure the phi0 legend is shown by default
    const phi0Legend = document.getElementById('phi0Legend');
    if (phi0Legend) {
        phi0Legend.style.display = 'block';
    }
}

// Process a single cell with Earth Engine
function processSingleCellEarthEngine(cellId) {
    if (!cellId) return;
    
    // Show loading indicator
    const detailsContainer = document.getElementById('cellDetails');
    const currentContent = detailsContainer.innerHTML;
    detailsContainer.innerHTML += `
        <div class="mt-3 text-center" id="eeProcessingIndicator">
            <div class="spinner-border text-success" role="status">
                <span class="visually-hidden">Processing...</span>
            </div>
            <p class="mt-2">Processing with Earth Engine...</p>
        </div>
    `;
    
    // Send request to process cell
    EarthEngine.processSingleCell(cellId)
        .then(result => {
            if (!result) {
                throw new Error('Failed to process cell');
            }
            
            // Reload cell details with new Earth Engine data
            return Promise.all([
                fetch(`${API_URL}/phi0-results/${cellId}`).then(resp => resp.json()),
                fetch(`${API_URL}/environmental-data/${cellId}`).then(resp => resp.json())
            ]).then(([phi0Data, envData]) => {
                displayCellDetails(phi0Data, envData, result);
            });
        })
        .catch(error => {
            console.error(`Error processing cell ${cellId} with Earth Engine:`, error);
            
            // Remove loading indicator
            const indicator = document.getElementById('eeProcessingIndicator');
            if (indicator) {
                indicator.remove();
            }
            
            // Show error message
            detailsContainer.innerHTML += `
                <div class="alert alert-danger mt-3">
                    Failed to process cell with Earth Engine: ${error.message}
                </div>
            `;
        });
}

// Start region processing
// This function moved to earth_engine.js

function startRegionProcessing() {
    // Get parameters from modal
    const maxCells = parseInt(document.getElementById('maxCellsInput').value) || 50;
    
    // Get selected datasets
    const datasetElements = document.querySelectorAll('#datasetsContainer input[type="checkbox"]:checked');
    const selectedDatasets = Array.from(datasetElements).map(el => {
        return el.id.replace('dataset-', '').replace(/-/g, '/');
    });
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('processRegionModal')).hide();
    
    // Start processing
    EarthEngine.processRegion().then(taskInfo => {
        if (!taskInfo) {
            showEarthEngineError('Failed to start processing task');
        }
    });
}
