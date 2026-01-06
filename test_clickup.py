#!/usr/bin/env python3
"""Test ClickUp functionality directly."""

import asyncio
import os
import sys
import logging

# Add the app directory to the path
sys.path.insert(0, '/Users/girda01/python/lpg-core-platform-api')

# Set minimal environment variables to avoid validation errors
os.environ['ERP_BASE_URL'] = 'http://dummy'
os.environ['DB_DSN'] = 'mssql+pyodbc://user:pass@SERVER/DB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes'

logging.basicConfig(level=logging.DEBUG)

async def test_clickup():
    """Test ClickUp functionality."""
    try:
        from app.adapters.clickup_client import ClickUpClient
        from app.domain.clickup.service import ClickUpService
        from app.domain.clickup.models import ClickUpTaskResponse
        from app.settings import settings

        print("✓ ClickUp imports successful")
        print(f"✓ ClickUp API key configured: {bool(settings.clickup_api_key)}")
        print(f"✓ ClickUp SAV folder ID: {settings.clickup_sav_folder_id}")
        print(f"✓ ClickUp Rabotage list ID: {settings.clickup_rabotage_list_id}")

        # Test service creation
        service = ClickUpService()
        print("✓ ClickUp service created")

        # Test the actual API call (this will likely fail without proper credentials)
        try:
            result = await service.get_sav_rabotage_tasks()
            print(f"✓ API call successful, got {len(result.tasks)} tasks")
            if result.tasks:
                print(f"  Sample task: {result.tasks[0].name}")
        except Exception as api_error:
            print(f"✗ API call failed (expected): {api_error}")
            print(f"  Type: {type(api_error)}")
            print(f"  Status code: {getattr(api_error, 'status_code', 'N/A')}")
            print(f"  Error code: {getattr(api_error, 'error_code', 'N/A')}")

    except Exception as e:
        print(f"✗ Setup error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_clickup())
