#!/usr/bin/env python3
"""
Database Initialization Script
=============================
This script initializes the database schema for the RE-Archaeology Agent.
It creates the re_archaeology schema and all required tables if they don't exist.

Usage:
------
python -m backend.models.init_db
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import create_database, database_exists
from dotenv import load_dotenv

# Add parent directory to path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, parent_dir)

# Import database models
from backend.models.database import Base
from backend.utils.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database schema."""
    logger.info(f"Using database URL: {settings.DATABASE_URL}")

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # Create database if it doesn't exist (will be skipped if database exists)
    try:
        if not database_exists(engine.url):
            create_database(engine.url)
            logger.info(f"Created database {engine.url.database}")
    except SQLAlchemyError as e:
        logger.warning(f"Unable to check or create database: {e}")
        logger.info("Continuing with schema creation...")

    try:
        # Drop all tables to ensure clean start
        with engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS public.environmental_data CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.phi0_results CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.data_processing_tasks CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.grid_cells CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.discussions CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.discussion_messages CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.map_states CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.seed_sites CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.psi0_attractors CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS public.agent_state CASCADE"))
            logger.info("Dropped existing tables for clean initialization")
            connection.commit()

        # Using default 'public' schema
        with engine.connect() as connection:
            # No need to create schema as 'public' exists by default
            connection.commit()
            logger.info("Using default 'public' schema for tables")

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully created all tables")
    except SQLAlchemyError as e:
        logger.error(f"Error creating schema or tables: {e}")
        return False

    logger.info("Database initialization completed successfully")
    return True

if __name__ == '__main__':
    load_dotenv()
    success = init_db()
    sys.exit(0 if success else 1)
