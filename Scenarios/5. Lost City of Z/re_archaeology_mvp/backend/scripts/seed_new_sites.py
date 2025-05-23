#!/usr/bin/env python3
"""
Seed New Reference Sites - Landívar and Cotoca
============================================
This script adds the new lidar-confirmed archaeological sites from the 2022 paper
to the backend database as seed sites.

Sites from: https://pmc.ncbi.nlm.nih.gov/articles/PMC9177426/#Sec2
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement
from datetime import datetime

# Add parent directory to path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, parent_dir)

from backend.models.database import SeedSite
from backend.utils.config import settings

def add_new_reference_sites():
    """Add Landívar and Cotoca sites to the database."""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # New lidar-confirmed sites from 2022 paper
        new_sites = [
            {
                "site_name": "Landívar",
                "site_description": "Lidar-confirmed pre-Columbian settlement discovered in 2022 research. Small site (~2km diameter) with 100% lidar coverage.",
                "site_type": "settlement",
                "confidence_level": "high",
                "lat": -15.2012842,
                "lon": -64.4677797,
                "source_reference": "PMC9177426 - Lidar reveals pre-Columbian urban centers in the Bolivian Amazon",
                "site_metadata": {
                    "discovery_year": 2022,
                    "detection_method": "lidar",
                    "coverage_percentage": 100,
                    "diameter_km": 2,
                    "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9177426/#Sec2",
                    "notes": "One of two larger settlements identified in recent research",
                    "distance_to_cotoca_km": 20
                }
            },
            {
                "site_name": "Cotoca",
                "site_description": "Lidar-confirmed pre-Columbian settlement discovered in 2022 research. Small site (~2km diameter) with 100% lidar coverage, located 20km from Landívar.",
                "site_type": "settlement", 
                "confidence_level": "high",
                "lat": -14.9898697,
                "lon": -64.5968503,
                "source_reference": "PMC9177426 - Lidar reveals pre-Columbian urban centers in the Bolivian Amazon",
                "site_metadata": {
                    "discovery_year": 2022,
                    "detection_method": "lidar", 
                    "coverage_percentage": 100,
                    "diameter_km": 2,
                    "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9177426/#Sec2",
                    "notes": "One of two larger settlements identified in recent research",
                    "distance_to_landivar_km": 20
                }
            }
        ]
        
        # Check if sites already exist and add them if not
        for site_data in new_sites:
            existing = db.query(SeedSite).filter(SeedSite.site_name == site_data["site_name"]).first()
            
            if existing:
                print(f"Site '{site_data['site_name']}' already exists, skipping...")
                continue
                
            # Create WKT point geometry
            geom = WKTElement(f"POINT({site_data['lon']} {site_data['lat']})", srid=4326)
            
            # Create new seed site
            new_site = SeedSite(
                site_name=site_data["site_name"],
                site_description=site_data["site_description"],
                site_type=site_data["site_type"],
                confidence_level=site_data["confidence_level"],
                geom=geom,
                source_reference=site_data["source_reference"],
                site_metadata=site_data["site_metadata"]
            )
            
            db.add(new_site)
            print(f"✅ Added new site: {site_data['site_name']} at ({site_data['lat']}, {site_data['lon']})")
        
        # Commit changes
        db.commit()
        print("✅ Successfully added new reference sites to database")
        
    except Exception as e:
        print(f"❌ Error adding sites: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == '__main__':
    success = add_new_reference_sites()
    sys.exit(0 if success else 1)
