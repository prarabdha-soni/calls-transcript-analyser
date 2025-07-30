#!/usr/bin/env python3
"""
Test script for AI insights module.
"""

import asyncio
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai_insights import analytics_processor


async def test_ai_insights():
    """Test AI insights module"""
    try:
        print("Testing AI insights module...")

        # Test basic functionality
        test_transcript = "Agent: Hello, how can I help you?\nCustomer: I'm interested in your product."

        print("Testing agent talk ratio...")
        ratio = analytics_processor.agent_talk_ratio(test_transcript)
        print(f"Agent talk ratio: {ratio}")

        print("Testing customer sentiment...")
        sentiment = analytics_processor.customer_sentiment(test_transcript)
        print(f"Customer sentiment: {sentiment}")

        print("Testing transcript embedding...")
        embedding = analytics_processor.transcript_embedding(test_transcript)
        print(f"Embedding length: {len(embedding)}")

        print("Testing process method...")
        agent_ratio, sentiment_score, embedding = analytics_processor.process(
            test_transcript
        )
        print(
            f"Process results - Agent ratio: {agent_ratio}, Sentiment: {sentiment_score}, Embedding length: {len(embedding)}"
        )

        print("AI insights module test completed successfully!")

    except Exception as e:
        print(f"Error during AI insights test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ai_insights())
