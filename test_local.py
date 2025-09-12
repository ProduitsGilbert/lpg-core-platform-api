#!/usr/bin/env python3
"""
Quick test script to run the API locally without Docker
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for local testing
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'
os.environ['LOGFIRE_IGNORE_NO_PROJECT'] = '1'
os.environ['ENABLE_SCHEDULER'] = 'false'
os.environ['ENABLE_OCR'] = 'false'
os.environ['ENABLE_AI_ASSISTANCE'] = 'false'
# Fix CORS_ORIGINS to be a JSON array
os.environ['CORS_ORIGINS'] = '["http://localhost:3000","http://localhost:8000"]'

if __name__ == "__main__":
    import uvicorn
    print("Starting LPG Core Platform API locally on http://localhost:7003")
    print("Press Ctrl+C to stop")
    print("\nHealth check: http://localhost:7003/healthz")
    print("API docs: http://localhost:7003/docs")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7003,
        reload=True,
        log_level="info"
    )