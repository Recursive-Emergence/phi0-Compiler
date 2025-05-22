"""
Earth Engine Data Pipeline Orchestrator
====================================
This module orchestrates the Earth Engine data processing pipeline,
managing the flow of data extraction and processing tasks.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
from sqlalchemy.orm import Session

from backend.data_processors.earth_engine.connector import EarthEngineConnector
from backend.data_processors.earth_engine.ndvi_processor import NDVIProcessor
from backend.data_processors.earth_engine.canopy_processor import CanopyProcessor
from backend.data_processors.earth_engine.env_features_processor import EnvironmentalFeatureProcessor
from backend.models.database import GridCell, EnvironmentalData, DataProcessingTask
from backend.utils.config import settings
from backend.core.agent_self_model.model import REAgentSelfModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EarthEnginePipeline:
    """
    Orchestrates the Earth Engine data processing pipeline.
    
    This class manages the execution of various data processing tasks,
    tracking their status and ensuring that all required data is collected
    for subsequent analysis steps.
    """
    
    def __init__(self, db_session: Session, agent_model: Optional[REAgentSelfModel] = None):
        """
        Initialize the Earth Engine pipeline
        
        Args:
            db_session: SQLAlchemy database session
            agent_model: Optional RE Agent self-model for state persistence
        """
        self.db = db_session
        self.agent = agent_model
        self.ee_connector = EarthEngineConnector()
        
        # Initialize processors
        self.ndvi_processor = NDVIProcessor(db_session)
        self.canopy_processor = CanopyProcessor(db_session)
        self.env_processor = EnvironmentalFeatureProcessor(db_session)
    
    def check_connections(self) -> Dict[str, bool]:
        """
        Check all connections required for the pipeline
        
        Returns:
            Dictionary with connection status for each component
        """
        return {
            "earth_engine": self.ee_connector.check_connection(),
            "database": self._check_db_connection()
        }
    
    def _check_db_connection(self) -> bool:
        """Check database connection"""
        try:
            # Simple query to check connection
            self.db.query(GridCell).first()
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def process_cell_complete(self, cell_id: str) -> Dict[str, Any]:
        """
        Process a single cell with all available data sources
        
        Args:
            cell_id: Grid cell ID
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "cell_id": cell_id,
            "timestamp": datetime.now().isoformat(),
            "tasks": {}
        }
        
        # Create task record
        task = DataProcessingTask(
            task_type="full_cell_processing",
            status="running",
            cell_id=cell_id,
            params={"sources": ["ndvi", "canopy", "terrain", "water"]},
            started_at=datetime.now()
        )
        self.db.add(task)
        self.db.commit()
        
        try:
            # Process NDVI
            logger.info(f"Processing NDVI for cell {cell_id}")
            ndvi_result = self.ndvi_processor.calculate_ndvi_for_cell(cell_id)
            results["tasks"]["ndvi"] = {"success": "error" not in ndvi_result}
            
            # Process canopy height
            logger.info(f"Processing canopy height for cell {cell_id}")
            canopy_result = self.canopy_processor.calculate_canopy_height_for_cell(cell_id)
            results["tasks"]["canopy"] = {"success": "error" not in canopy_result}
            
            # Process terrain features
            logger.info(f"Processing terrain features for cell {cell_id}")
            terrain_result = self.env_processor.calculate_terrain_features(cell_id)
            results["tasks"]["terrain"] = {"success": "error" not in terrain_result}
            
            # Process water proximity
            logger.info(f"Processing water proximity for cell {cell_id}")
            water_result = self.env_processor.calculate_water_proximity(cell_id)
            results["tasks"]["water"] = {"success": "error" not in water_result}
            
            # Update task record
            task.status = "completed"
            task.completed_at = datetime.now()
            task.results = results
            self.db.commit()
            
            # If agent model is available, record the processing
            if self.agent:
                self.agent.add_action({
                    "action": "process_cell",
                    "cell_id": cell_id,
                    "results": results
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in cell processing pipeline for {cell_id}: {e}")
            # Update task record with error
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self.db.commit()
            
            return {
                "cell_id": cell_id,
                "error": f"Processing pipeline failed: {str(e)}",
                "tasks": results.get("tasks", {})
            }
    
    def process_region(self,
                     bounding_box: List[float],
                     data_sources: List[str] = None,
                     max_cells: int = 100) -> Dict[str, Any]:
        """
        Process all cells in a region with selected data sources
        
        Args:
            bounding_box: [min_lon, min_lat, max_lon, max_lat]
            data_sources: List of data sources to process ("ndvi", "canopy", "terrain", "water")
            max_cells: Maximum number of cells to process
            
        Returns:
            Dictionary with processing results
        """
        if data_sources is None:
            data_sources = ["ndvi", "canopy", "terrain", "water"]
            
        # Query cells in the bounding box
        cells = self.db.query(GridCell).filter(
            GridCell.lon_min >= bounding_box[0],
            GridCell.lat_min >= bounding_box[1],
            GridCell.lon_max <= bounding_box[2],
            GridCell.lat_max <= bounding_box[3]
        ).limit(max_cells).all()
        
        # Create task record
        task = DataProcessingTask(
            task_type="region_processing",
            status="running",
            params={
                "bounding_box": bounding_box,
                "data_sources": data_sources,
                "max_cells": max_cells
            },
            started_at=datetime.now()
        )
        self.db.add(task)
        self.db.commit()
        
        results = {
            "task_id": task.id,
            "bounding_box": bounding_box,
            "data_sources": data_sources,
            "total_cells": len(cells),
            "processed_cells": 0,
            "errors": 0,
            "cell_results": {}
        }
        
        try:
            # Process each cell with requested data sources
            for cell in cells:
                cell_result = {"cell_id": cell.cell_id, "sources": {}}
                
                try:
                    if "ndvi" in data_sources:
                        ndvi_result = self.ndvi_processor.calculate_ndvi_for_cell(cell.cell_id)
                        cell_result["sources"]["ndvi"] = {"success": "error" not in ndvi_result}
                        
                    if "canopy" in data_sources:
                        canopy_result = self.canopy_processor.calculate_canopy_height_for_cell(cell.cell_id)
                        cell_result["sources"]["canopy"] = {"success": "error" not in canopy_result}
                        
                    if "terrain" in data_sources:
                        terrain_result = self.env_processor.calculate_terrain_features(cell.cell_id)
                        cell_result["sources"]["terrain"] = {"success": "error" not in terrain_result}
                        
                    if "water" in data_sources:
                        water_result = self.env_processor.calculate_water_proximity(cell.cell_id)
                        cell_result["sources"]["water"] = {"success": "error" not in water_result}
                    
                    results["processed_cells"] += 1
                except Exception as e:
                    logger.error(f"Error processing cell {cell.cell_id}: {e}")
                    cell_result["error"] = str(e)
                    results["errors"] += 1
                
                results["cell_results"][cell.cell_id] = cell_result
            
            # Update task record
            task.status = "completed"
            task.completed_at = datetime.now()
            task.results = results
            self.db.commit()
            
            # If agent model is available, record the processing
            if self.agent:
                self.agent.add_action({
                    "action": "process_region",
                    "bounding_box": bounding_box,
                    "sources": data_sources,
                    "cells_processed": results["processed_cells"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in region processing pipeline: {e}")
            # Update task record with error
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.results = results
            self.db.commit()
            
            return {
                "task_id": task.id,
                "error": f"Processing pipeline failed: {str(e)}",
                "partial_results": results
            }
    
    def process_cells_batch(self, 
                          cell_ids: List[str], 
                          data_sources: List[str] = None) -> Dict[str, Any]:
        """
        Process a batch of specific cells with selected data sources
        
        Args:
            cell_ids: List of cell IDs to process
            data_sources: List of data sources to process ("ndvi", "canopy", "terrain", "water")
            
        Returns:
            Dictionary with processing results
        """
        if data_sources is None:
            data_sources = ["ndvi", "canopy", "terrain", "water"]
            
        # Create task record
        task = DataProcessingTask(
            task_type="batch_processing",
            status="running",
            params={
                "cell_ids": cell_ids,
                "data_sources": data_sources
            },
            started_at=datetime.now()
        )
        self.db.add(task)
        self.db.commit()
        
        results = {
            "task_id": task.id,
            "data_sources": data_sources,
            "total_cells": len(cell_ids),
            "processed_cells": 0,
            "errors": 0,
            "cell_results": {}
        }
        
        try:
            # Process each cell with requested data sources
            for cell_id in cell_ids:
                cell_result = {"cell_id": cell_id, "sources": {}}
                
                try:
                    if "ndvi" in data_sources:
                        ndvi_result = self.ndvi_processor.calculate_ndvi_for_cell(cell_id)
                        cell_result["sources"]["ndvi"] = {"success": "error" not in ndvi_result}
                        
                    if "canopy" in data_sources:
                        canopy_result = self.canopy_processor.calculate_canopy_height_for_cell(cell_id)
                        cell_result["sources"]["canopy"] = {"success": "error" not in canopy_result}
                        
                    if "terrain" in data_sources:
                        terrain_result = self.env_processor.calculate_terrain_features(cell_id)
                        cell_result["sources"]["terrain"] = {"success": "error" not in terrain_result}
                        
                    if "water" in data_sources:
                        water_result = self.env_processor.calculate_water_proximity(cell_id)
                        cell_result["sources"]["water"] = {"success": "error" not in water_result}
                    
                    results["processed_cells"] += 1
                except Exception as e:
                    logger.error(f"Error processing cell {cell_id}: {e}")
                    cell_result["error"] = str(e)
                    results["errors"] += 1
                
                results["cell_results"][cell_id] = cell_result
            
            # Update task record
            task.status = "completed"
            task.completed_at = datetime.now()
            task.results = results
            self.db.commit()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing pipeline: {e}")
            # Update task record with error
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.results = results
            self.db.commit()
            
            return {
                "task_id": task.id,
                "error": f"Processing pipeline failed: {str(e)}",
                "partial_results": results
            }
