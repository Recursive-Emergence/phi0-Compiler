from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

Base = declarative_base()

class GridCell(Base):
    __tablename__ = 'grid_cells'
    __table_args__ = {'schema': 'public'}  # Using 'public' schema which exists by default
    
    id = Column(Integer, primary_key=True)
    cell_id = Column(String(50), unique=True, nullable=False)
    geom = Column(Geometry('POLYGON', srid=4326), nullable=False)
    centroid = Column(Geometry('POINT', srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EnvironmentalData(Base):
    __tablename__ = 'environmental_data'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    cell_id = Column(String(50), ForeignKey('public.grid_cells.cell_id'))
    ndvi_mean = Column(Float)
    ndvi_std = Column(Float)
    canopy_height_mean = Column(Float)
    canopy_height_std = Column(Float)
    elevation_mean = Column(Float)
    elevation_std = Column(Float)
    slope_mean = Column(Float)
    slope_std = Column(Float)
    water_proximity = Column(Float)
    raw_data = Column(JSONB)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

class Phi0Result(Base):
    __tablename__ = 'phi0_results'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    cell_id = Column(String(50), ForeignKey('public.grid_cells.cell_id'))
    phi0_score = Column(Float, nullable=False)
    confidence_interval = Column(Float)
    site_type_prediction = Column(String(50))
    contradiction_patterns = Column(JSONB)
    calculation_metadata = Column(JSONB)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

class SeedSite(Base):
    __tablename__ = 'seed_sites'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    site_name = Column(String(100), nullable=False)
    site_description = Column(Text)
    site_type = Column(String(50))
    confidence_level = Column(String(20))
    geom = Column(Geometry('POINT', srid=4326), nullable=False)
    source_reference = Column(Text)
    site_metadata = Column(JSONB)  # Renamed from 'metadata' to avoid conflict with SQLAlchemy
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Psi0Attractor(Base):
    __tablename__ = 'psi0_attractors'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    attractor_name = Column(String(100), nullable=False)
    attractor_type = Column(String(50))
    strength = Column(Float)
    influence_radius = Column(Float)
    symbolic_metadata = Column(JSONB)
    geom = Column(Geometry('POINT', srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentState(Base):
    __tablename__ = 'agent_state'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    state_snapshot = Column(JSONB, nullable=False)
    memory_context = Column(JSONB)
    reasoning_chains = Column(JSONB)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class Discussion(Base):
    __tablename__ = 'discussions'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='open')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class DiscussionMessage(Base):
    __tablename__ = 'discussion_messages'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey('public.discussions.id', ondelete='CASCADE'))
    parent_message_id = Column(Integer, ForeignKey('public.discussion_messages.id'))
    author_type = Column(String(50), nullable=False)
    author_name = Column(String(100), nullable=False)
    message_content = Column(Text, nullable=False)
    map_state_reference = Column(JSONB)
    attachment_urls = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MapState(Base):
    __tablename__ = 'map_states'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    state_id = Column(String(50), unique=True, nullable=False)
    state_params = Column(JSONB, nullable=False)
    title = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))

class DataProcessingTask(Base):
    __tablename__ = 'data_processing_tasks'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='queued')
    cell_id = Column(String(50), ForeignKey('public.grid_cells.cell_id'))
    params = Column(JSONB)
    results = Column(JSONB)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
