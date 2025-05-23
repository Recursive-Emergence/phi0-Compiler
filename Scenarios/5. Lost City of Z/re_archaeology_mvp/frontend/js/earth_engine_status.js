// Show Earth Engine error message
function showEarthEngineError(message) {
    // Create error container if not exists
    let errorContainer = document.getElementById('earthEngineErrorContainer');
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.id = 'earthEngineErrorContainer';
        errorContainer.className = 'earth-engine-error alert alert-danger alert-dismissible fade show';
        errorContainer.role = 'alert';
        errorContainer.style.position = 'fixed';
        errorContainer.style.bottom = '20px';
        errorContainer.style.left = '20px';
        errorContainer.style.zIndex = '9999';
        errorContainer.style.maxWidth = '500px';
        document.body.appendChild(errorContainer);
    }
    
    // Set message and ensure it's visible
    errorContainer.innerHTML = `
        <strong>Earth Engine Error:</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Show error
    errorContainer.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        if (errorContainer.parentNode) {
            errorContainer.style.display = 'none';
        }
    }, 10000);
}

// Show Earth Engine task status
function showEarthEngineTaskStatus(message, progress) {
    // Create status container if not exists
    let statusContainer = document.querySelector('.earth-engine-status');
    if (!statusContainer) {
        statusContainer = document.createElement('div');
        statusContainer.className = 'earth-engine-status';
        document.body.appendChild(statusContainer);
        
        statusContainer.innerHTML = `
            <div class="ee-status-header">
                <span>Earth Engine Processing</span>
                <button type="button" class="btn-close btn-close-white btn-sm" aria-label="Close"></button>
            </div>
            <div class="ee-status-body">
                <div class="status-message mb-2"></div>
                <div class="progress">
                    <div class="progress-bar bg-success" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;
        
        // Wire up close button
        statusContainer.querySelector('.btn-close').addEventListener('click', () => {
            statusContainer.style.display = 'none';
        });
    }
    
    // Update status
    statusContainer.querySelector('.status-message').textContent = message;
    statusContainer.querySelector('.progress-bar').style.width = `${progress}%`;
    statusContainer.querySelector('.progress-bar').setAttribute('aria-valuenow', progress);
    
    // Show status
    statusContainer.style.display = 'block';
}
