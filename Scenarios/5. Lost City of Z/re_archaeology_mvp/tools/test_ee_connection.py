#!/usr/bin/env python
"""
Earth Engine Connection Test
===========================

Simple script to test Earth Engine authentication and connection.
Run this script to verify that Earth Engine is properly configured.
"""

import os
import sys
import ee
import argparse
from dotenv import load_dotenv

def test_ee_connection(service_account=None, key_file=None):
    """Test Earth Engine connection using specified credentials"""
    try:
        # Initialize Earth Engine
        if service_account and key_file:
            print(f"Authenticating with service account: {service_account}")
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials)
        else:
            print("Authenticating with application default credentials")
            ee.Initialize()
        
        # Test API with a simple operation
        print("Testing Earth Engine API...")
        image = ee.Image('NASA/NASADEM_HGT/001')
        info = image.getInfo()
        
        # Check if we got a valid response
        if info and 'type' in info:
            print("✅ Earth Engine connection successful!")
            print(f"Image type: {info['type']}")
            return True
        else:
            print("❌ Got response from Earth Engine, but it seems incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Earth Engine connection failed: {e}")
        return False

def main():
    """Main function to test Earth Engine connection"""
    parser = argparse.ArgumentParser(description='Test Earth Engine connection')
    parser.add_argument('--service-account', help='Service account email for authentication')
    parser.add_argument('--key-file', help='Path to service account key file')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # If command-line arguments are provided, use them
    service_account = args.service_account
    key_file = args.key_file
    
    # If not provided via command line, try to get from environment
    if not service_account:
        service_account = os.getenv('EE_SERVICE_ACCOUNT')
    
    if not key_file:
        key_file = os.getenv('EE_PRIVATE_KEY_FILE')
    
    # Test connection
    success = test_ee_connection(service_account, key_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
