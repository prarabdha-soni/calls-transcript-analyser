#!/usr/bin/env python3
"""
Script to check database contents.
"""

import asyncio
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import func

from app.database import get_async_db
from app.models import Call


async def check_database():
    """Check database contents"""
    try:
        async for db in get_async_db():
            # Count total calls
            result = await db.execute(func.count(Call.call_id))
            count = result.scalar()
            print(f"Total calls in database: {count}")

            # Get a sample call
            from sqlalchemy import select

            sample_call = await db.execute(select(Call).limit(1))
            call = sample_call.scalar_one_or_none()
            if call:
                print(f"Sample call ID: {call.call_id}")
                print(f"Agent ID: {call.agent_id}")
                print(f"Duration: {call.duration_seconds} seconds")
                print(f"Agent talk ratio: {call.agent_talk_ratio}")
                print(f"Sentiment score: {call.customer_sentiment_score}")

            break

    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_database())
