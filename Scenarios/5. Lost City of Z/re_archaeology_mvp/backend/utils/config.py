import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Base configuration
    PROJECT_NAME: str = "RE-Archaeology Agent"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://re_archaeology:re_archaeology_pass@localhost:5432/re_archaeology_db")
    
    # Extract database name from URL for initialization purposes
    @property
    def DATABASE_NAME(self) -> str:
        # Parse the database name from the URL
        # Format is typically: postgresql://user:password@host:port/dbname
        parts = self.DATABASE_URL.split('/')
        if len(parts) > 3:
            return parts[-1]
        return "postgres"  # Default to postgres if not specified
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Earth Engine configuration
    EE_AUTH_METHOD: str = os.getenv("EE_AUTH_METHOD", "application_default")
    EE_SERVICE_ACCOUNT: str = os.getenv("EE_SERVICE_ACCOUNT", "")
    EE_PRIVATE_KEY_FILE: str = os.getenv("EE_PRIVATE_KEY_FILE", "")
    EE_PROJECT_ID: str = os.getenv("EE_PROJECT_ID", "")
    
    # Data paths
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"))
    
    # Grid configuration
    DEFAULT_GRID_SIZE_DEGREES: float = 0.01  # Roughly 1km at equator
    
    # Contradiction detection parameters
    NDVI_CANOPY_CONTRADICTION_THRESHOLD: float = 0.3
    
    # Agent configuration
    AGENT_MEMORY_SIZE: int = 1000
    AGENT_STATE_PERSISTENCE_INTERVAL: int = 600  # Save state every 10 minutes

    class Config:
        case_sensitive = True

settings = Settings()

# Create required directories
os.makedirs(settings.DATA_DIR, exist_ok=True)
