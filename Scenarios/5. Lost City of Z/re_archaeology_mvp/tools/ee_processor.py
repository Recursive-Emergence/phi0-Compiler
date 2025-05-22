#!/usr/bin/env python
"""
Earth Engine Processor CLI
=========================

Command-line tool for processing Earth Engine data.
This tool allows for running Earth Engine data extraction tasks
from the command line, which is useful for initial data loading,
testing, and manual processing tasks.
"""

import argparse
import sys
import os
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import redis
from typing import Dict, List, Any, Optional

# Add the parent directory to sys.path to allow importing from the backend package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_processors.earth_engine.pipeline import EarthEnginePipeline
from backend.core.agent_self_model.model import REAgentSelfModel
from backend.models.database import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ee_processor.log")
    ]
)

logger = logging.getLogger(__name__)

def setup_database():
    """Set up database connection"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql://re_archaeology:re_archaeology_pass@localhost:5432/re_archaeology_db")
    
    # Create engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    return session

def setup_redis():
    """Set up Redis connection"""
    # Load environment variables if not already loaded
    load_dotenv()
    
    # Get Redis URL from environment or use default
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Create Redis client
    try:
        client = redis.from_url(redis_url)
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def process_region(args):
    """Process all cells in a region"""
    session = setup_database()
    redis_client = setup_redis()
    
    try:
        # Set up agent model if Redis is available
        agent_model = REAgentSelfModel(session, redis_client) if redis_client else None
        
        # Create pipeline
        pipeline = EarthEnginePipeline(session, agent_model)
        
        # Parse bounding box
        try:
            bbox = [float(x) for x in args.bbox.split(',')]
            if len(bbox) != 4:
                raise ValueError("Bounding box must have 4 values: min_lon,min_lat,max_lon,max_lat")
        except Exception as e:
            logger.error(f"Failed to parse bounding box: {e}")
            return
        
        # Parse data sources
        data_sources = args.sources.split(',') if args.sources else None
        
        # Process region
        logger.info(f"Processing region {bbox} with sources {data_sources}")
        result = pipeline.process_region(
            bounding_box=bbox,
            data_sources=data_sources,
            max_cells=args.max_cells
        )
        
        # Print result summary
        print(f"Region processing complete!")
        print(f"Total cells: {result.get('total_cells', 0)}")
        print(f"Processed: {result.get('processed_cells', 0)}")
        print(f"Errors: {result.get('errors', 0)}")
        
        # Save detailed results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Detailed results saved to {args.output}")
            
    finally:
        session.close()

def process_cells(args):
    """Process specific cells"""
    session = setup_database()
    redis_client = setup_redis()
    
    try:
        # Set up agent model if Redis is available
        agent_model = REAgentSelfModel(session, redis_client) if redis_client else None
        
        # Create pipeline
        pipeline = EarthEnginePipeline(session, agent_model)
        
        # Parse cell IDs
        cell_ids = args.cell_ids.split(',')
        
        # Parse data sources
        data_sources = args.sources.split(',') if args.sources else None
        
        # Process cells
        logger.info(f"Processing cells {cell_ids} with sources {data_sources}")
        result = pipeline.process_cells_batch(
            cell_ids=cell_ids,
            data_sources=data_sources
        )
        
        # Print result summary
        print(f"Cell processing complete!")
        print(f"Total cells: {result.get('total_cells', 0)}")
        print(f"Processed: {result.get('processed_cells', 0)}")
        print(f"Errors: {result.get('errors', 0)}")
        
        # Save detailed results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Detailed results saved to {args.output}")
            
    finally:
        session.close()

def check_status(args):
    """Check Earth Engine connection status"""
    session = setup_database()
    
    try:
        # Create pipeline
        pipeline = EarthEnginePipeline(session)
        
        # Check connections
        status = pipeline.check_connections()
        
        # Print status
        print("Earth Engine Connection Status:")
        for service, is_connected in status.items():
            print(f"  - {service}: {'CONNECTED' if is_connected else 'DISCONNECTED'}")
            
    finally:
        session.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Process Earth Engine data for RE-Archaeology Agent')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check Earth Engine connection status')
    
    # Process region command
    region_parser = subparsers.add_parser('process-region', help='Process all cells in a region')
    region_parser.add_argument('--bbox', required=True, help='Bounding box in format: min_lon,min_lat,max_lon,max_lat')
    region_parser.add_argument('--sources', help='Data sources to process (comma-separated): ndvi,canopy,terrain,water')
    region_parser.add_argument('--max-cells', type=int, default=100, help='Maximum number of cells to process')
    region_parser.add_argument('--output', help='Output file to save detailed results (JSON)')
    
    # Process cells command
    cells_parser = subparsers.add_parser('process-cells', help='Process specific cells')
    cells_parser.add_argument('--cell-ids', required=True, help='Cell IDs to process (comma-separated)')
    cells_parser.add_argument('--sources', help='Data sources to process (comma-separated): ndvi,canopy,terrain,water')
    cells_parser.add_argument('--output', help='Output file to save detailed results (JSON)')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        check_status(args)
    elif args.command == 'process-region':
        process_region(args)
    elif args.command == 'process-cells':
        process_cells(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
