#!/usr/bin/env python3
"""
Simple database connection test script.
"""

import asyncio
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_async_db, init_db


async def test_db_connection():
    """Test database connection"""
    try:
        print("Testing database connection...")

        # Initialize database
        await init_db()
        print("Database initialized successfully")

        # Test getting a session
        async for db in get_async_db():
            print("Database session created successfully")
            # Test a simple query
            from sqlalchemy import text

            result = await db.execute(text("SELECT 1"))
            print("Database query executed successfully")
            break

        print("Database connection test completed successfully")

    except Exception as e:
        print(f"Error during database test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_db_connection())
