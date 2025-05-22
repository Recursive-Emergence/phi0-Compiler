"""
Earth Engine Authentication Helper
================================

This module provides helper functions for Google Earth Engine authentication,
supporting both service account and application default credentials.
"""

import os
import json
import logging
from google.oauth2 import service_account
import ee
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def authenticate_earth_engine():
    """
    Authenticate with Google Earth Engine using credentials from environment variables.
    
    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        # Check authentication method from settings
        auth_method = settings.EE_AUTH_METHOD.lower()
        
        if auth_method == 'service_account':
            logger.info("Using service account authentication for Earth Engine")
            return _authenticate_with_service_account()
        else:
            logger.info("Using application default credentials for Earth Engine")
            return _authenticate_with_application_default()
            
    except Exception as e:
        logger.error(f"Earth Engine authentication failed: {e}")
        return False

def _authenticate_with_service_account():
    """
    Authenticate with Google Earth Engine using a service account.
    
    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        # Check for required settings
        if not settings.EE_SERVICE_ACCOUNT:
            logger.error("EE_SERVICE_ACCOUNT environment variable not set")
            return False
            
        if not settings.EE_PRIVATE_KEY_FILE:
            logger.error("EE_PRIVATE_KEY_FILE environment variable not set")
            return False
            
        # Check if key file exists
        if not os.path.isfile(settings.EE_PRIVATE_KEY_FILE):
            logger.error(f"Private key file not found: {settings.EE_PRIVATE_KEY_FILE}")
            return False
            
        # Initialize with service account credentials
        credentials = ee.ServiceAccountCredentials(
            settings.EE_SERVICE_ACCOUNT,
            settings.EE_PRIVATE_KEY_FILE
        )
        
        ee.Initialize(credentials)
        logger.info(f"Initialized Earth Engine with service account {settings.EE_SERVICE_ACCOUNT}")
        return True
        
    except Exception as e:
        logger.error(f"Service account authentication failed: {e}")
        return False

def _authenticate_with_application_default():
    """
    Authenticate with Google Earth Engine using application default credentials.
    
    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        # Initialize with application default credentials
        ee.Initialize()
        logger.info("Initialized Earth Engine with application default credentials")
        return True
        
    except Exception as e:
        logger.error(f"Application default authentication failed: {e}")
        return False

def get_authentication_status():
    """
    Check if Earth Engine is authenticated.
    
    Returns:
        dict: Authentication status information
    """
    try:
        # Try a simple operation to check authentication
        info = ee.Number(1).getInfo()
        
        # Determine authentication method that was used
        auth_method = "unknown"
        if hasattr(ee, "data") and hasattr(ee.data, "_credentials"):
            if hasattr(ee.data._credentials, "service_account_email"):
                auth_method = "service_account"
                service_account = ee.data._credentials.service_account_email
            else:
                auth_method = "application_default"
                service_account = None
        
        return {
            "authenticated": True,
            "auth_method": auth_method,
            "service_account": service_account if auth_method == "service_account" else None,
            "project_id": settings.EE_PROJECT_ID or None
        }
        
    except Exception as e:
        return {
            "authenticated": False,
            "auth_method": settings.EE_AUTH_METHOD,
            "error": str(e)
        }
