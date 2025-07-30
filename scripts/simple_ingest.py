#!/usr/bin/env python3
"""
Simplified data ingestion script for testing.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_async_db
from app.models import Call


async def simple_ingest():
    """Simple ingestion test"""
    try:
        print("Starting simple ingestion test...")

        async for db in get_async_db():
            # Create a simple test call
            test_call = Call(
                call_id="TEST_CALL_001",
                agent_id="AGENT_001",
                customer_id="CUST_001",
                language="en",
                start_time=datetime.now(),
                duration_seconds=300,
                transcript="Agent: Hello, how can I help you?\nCustomer: I'm interested in your product.",
                agent_talk_ratio=0.5,
                customer_sentiment_score=0.0,
                embedding="test_embedding",
            )

            db.add(test_call)
            await db.commit()
            print("Test call inserted successfully!")
            break

        print("Simple ingestion test completed successfully!")

    except Exception as e:
        print(f"Error during simple ingestion: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_ingest())
