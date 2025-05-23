#!/usr/bin/env python3
"""
Script to drop and recreate the grid_cells table.
This will fix the missing columns issue.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

print(f"Connecting to database: {database_url}")

# Create engine
engine = create_engine(database_url)

try:
    with engine.connect() as connection:
        # First check if the table exists
        result = connection.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'grid_cells')"))
        table_exists = result.scalar()
        
        if table_exists:
            print("Dropping grid_cells table...")
            # Drop dependent tables first (foreign key constraints)
            connection.execute(text("DROP TABLE IF EXISTS public.environmental_data CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.phi0_results CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.data_processing_tasks CASCADE"))
            
            # Now drop the grid_cells table
            connection.execute(text("DROP TABLE IF EXISTS public.grid_cells CASCADE"))
            print("Table dropped successfully")
        
        # Create the grid_cells table with the new columns
        print("Creating grid_cells table with all required columns...")
        connection.execute(text("""
        CREATE TABLE public.grid_cells (
            id SERIAL PRIMARY KEY,
            cell_id VARCHAR(50) UNIQUE NOT NULL,
            lon_min FLOAT,
            lon_max FLOAT,
            lat_min FLOAT,
            lat_max FLOAT,
            geom GEOMETRY(POLYGON, 4326) NOT NULL,
            centroid GEOMETRY(POINT, 4326),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """))
        print("Grid cells table created successfully with all columns")
        
        # Commit the transaction
        connection.commit()
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print("All done! Table has been recreated with the required columns.")
