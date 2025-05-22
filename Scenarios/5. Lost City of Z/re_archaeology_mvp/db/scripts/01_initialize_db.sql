-- Initialize PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create schema
CREATE SCHEMA IF NOT EXISTS re_archaeology;

-- Create grid cells table
CREATE TABLE re_archaeology.grid_cells (
    id SERIAL PRIMARY KEY,
    cell_id VARCHAR(50) UNIQUE NOT NULL,
    geom GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid GEOMETRY(POINT, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for grid cells
CREATE INDEX grid_cells_geom_idx ON re_archaeology.grid_cells USING GIST(geom);
CREATE INDEX grid_cells_centroid_idx ON re_archaeology.grid_cells USING GIST(centroid);

-- Create environmental data table
CREATE TABLE re_archaeology.environmental_data (
    id SERIAL PRIMARY KEY,
    cell_id VARCHAR(50) REFERENCES re_archaeology.grid_cells(cell_id),
    ndvi_mean FLOAT,
    ndvi_std FLOAT,
    canopy_height_mean FLOAT,
    canopy_height_std FLOAT,
    elevation_mean FLOAT,
    elevation_std FLOAT,
    slope_mean FLOAT,
    slope_std FLOAT,
    water_proximity FLOAT,
    raw_data JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on cell_id for environmental data
CREATE INDEX env_data_cell_id_idx ON re_archaeology.environmental_data(cell_id);

-- Create phi0 resonance results table
CREATE TABLE re_archaeology.phi0_results (
    id SERIAL PRIMARY KEY,
    cell_id VARCHAR(50) REFERENCES re_archaeology.grid_cells(cell_id),
    phi0_score FLOAT NOT NULL,
    confidence_interval FLOAT,
    site_type_prediction VARCHAR(50),
    contradiction_patterns JSONB,
    calculation_metadata JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on cell_id and phi0_score
CREATE INDEX phi0_results_cell_id_idx ON re_archaeology.phi0_results(cell_id);
CREATE INDEX phi0_results_score_idx ON re_archaeology.phi0_results(phi0_score);

-- Create seed site catalog table
CREATE TABLE re_archaeology.seed_sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    site_description TEXT,
    site_type VARCHAR(50),
    confidence_level VARCHAR(20), -- confirmed, probable, theoretical
    geom GEOMETRY(POINT, 4326) NOT NULL,
    source_reference TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for seed sites
CREATE INDEX seed_sites_geom_idx ON re_archaeology.seed_sites USING GIST(geom);

-- Create psi0 attractors table
CREATE TABLE re_archaeology.psi0_attractors (
    id SERIAL PRIMARY KEY,
    attractor_name VARCHAR(100) NOT NULL,
    attractor_type VARCHAR(50),
    strength FLOAT,
    influence_radius FLOAT,
    symbolic_metadata JSONB,
    geom GEOMETRY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for psi0 attractors
CREATE INDEX psi0_attractors_geom_idx ON re_archaeology.psi0_attractors USING GIST(geom);

-- Create agent state table
CREATE TABLE re_archaeology.agent_state (
    id SERIAL PRIMARY KEY,
    state_snapshot JSONB NOT NULL,
    memory_context JSONB,
    reasoning_chains JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create discussions table
CREATE TABLE re_archaeology.discussions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create discussion messages table
CREATE TABLE re_archaeology.discussion_messages (
    id SERIAL PRIMARY KEY,
    discussion_id INTEGER REFERENCES re_archaeology.discussions(id) ON DELETE CASCADE,
    parent_message_id INTEGER REFERENCES re_archaeology.discussion_messages(id),
    author_type VARCHAR(50) NOT NULL, -- 'agent', 'human'
    author_name VARCHAR(100) NOT NULL,
    message_content TEXT NOT NULL,
    map_state_reference JSONB, -- Stores URL parameters for map state
    attachment_urls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on discussion_id
CREATE INDEX disc_messages_disc_id_idx ON re_archaeology.discussion_messages(discussion_id);
CREATE INDEX disc_messages_parent_idx ON re_archaeology.discussion_messages(parent_message_id);

-- Create table to store map states
CREATE TABLE re_archaeology.map_states (
    id SERIAL PRIMARY KEY,
    state_id VARCHAR(50) UNIQUE NOT NULL, -- URL-friendly ID
    state_params JSONB NOT NULL, -- Serialized map parameters
    title VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- Create table to store data processing tasks
CREATE TABLE re_archaeology.data_processing_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL, -- 'region_processing', 'batch_processing', 'full_cell_processing'
    status VARCHAR(20) NOT NULL DEFAULT 'queued', -- 'queued', 'running', 'completed', 'failed'
    cell_id VARCHAR(50) REFERENCES re_archaeology.grid_cells(cell_id),
    params JSONB, -- Task parameters
    results JSONB, -- Task results
    error_message TEXT, -- Error details if failed
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on task status and type
CREATE INDEX data_proc_tasks_status_idx ON re_archaeology.data_processing_tasks(status);
CREATE INDEX data_proc_tasks_type_idx ON re_archaeology.data_processing_tasks(task_type);
CREATE INDEX data_proc_tasks_cell_idx ON re_archaeology.data_processing_tasks(cell_id);

-- Grant privileges
ALTER SCHEMA re_archaeology OWNER TO re_archaeology;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA re_archaeology TO re_archaeology;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA re_archaeology TO re_archaeology;
