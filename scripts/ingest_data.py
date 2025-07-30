#!/usr/bin/env python3
"""
Data ingestion script for the Sales Call Analytics API.
This script generates synthetic call data and ingests it into the database.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_async_db
from app.data_ingestion import run_ingestion_pipeline


async def main():
    """Main function to run the ingestion pipeline"""
    try:
        db = await get_async_db()
        await run_ingestion_pipeline(db, num_calls=200)
    except Exception as e:
        print(f"Error during data ingestion: {e}")


if __name__ == "__main__":
    asyncio.run(main())
