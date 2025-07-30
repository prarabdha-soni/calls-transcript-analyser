#!/usr/bin/env python3
"""
Test script to verify ML models are working correctly
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai_insights import analytics_processor
from app.config import settings


def test_ml_models():
    test_transcript = """
Agent: Thank you for your time today. How can I help you?
Customer: I'm interested in learning more about your product.
Agent: That's great! Let me walk you through the benefits.
Customer: This sounds promising. What's the next step?
Agent: I'm confident we can find the right solution for you.
Customer: I'm very happy with what I've heard so far!
"""
    try:
        sentiment_score = analytics_processor.customer_sentiment(test_transcript)
    except Exception as e:
        print(f"Sentiment Analysis Failed: {e}")
    try:
        embedding = analytics_processor.transcript_embedding(test_transcript)
        embedding_list = (
            analytics_processor.embedding_model.encode(test_transcript).tolist()
            if analytics_processor.embedding_model
            else []
        )
    except Exception as e:
        print(f"Embedding Generation Failed: {e}")
    try:
        talk_ratio = analytics_processor.agent_talk_ratio(test_transcript)
    except Exception as e:
        print(f"Talk Ratio Calculation Failed: {e}")
    try:
        agent_ratio, sentiment_score, embedding = analytics_processor.process(
            test_transcript
        )
    except Exception as e:
        print(f"Complete Processing Failed: {e}")
    if not analytics_processor.embedding_model:
        print("Embedding Model: Not loaded (using fallback)")
    if not analytics_processor.sentiment_model:
        print("Sentiment Model: Not loaded (using fallback)")


if __name__ == "__main__":
    test_ml_models()
