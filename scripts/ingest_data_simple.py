#!/usr/bin/env python3
"""
Simplified data ingestion script without AI insights.
"""

import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models import Call

fake = Faker()


class SimpleCallGenerator:
    """Generate synthetic call data without AI processing"""

    def __init__(self):
        self.sales_topics = [
            "product demonstration",
            "pricing discussion",
            "objection handling",
            "closing techniques",
            "follow-up scheduling",
            "competitor comparison",
            "feature benefits",
            "customer needs analysis",
            "solution presentation",
        ]

        self.agent_phrases = [
            "Thank you for your time today. How can I help you?",
            "I understand your concern. Let me address that for you.",
            "That's a great question. Here's what I can offer...",
            "Based on your needs, I think our solution would be perfect.",
            "Would you like me to send you more information?",
            "I'm confident we can find the right solution for you.",
            "Let me walk you through the benefits of our product.",
            "I appreciate you sharing that with me.",
            "How does that sound to you?",
            "Is there anything else you'd like to know?",
        ]

        self.customer_phrases = [
            "I'm interested in learning more about your product.",
            "What are your pricing options?",
            "I'm not sure this is the right fit for us.",
            "Can you tell me more about the features?",
            "I'm concerned about the implementation timeline.",
            "How does this compare to your competitors?",
            "I need to think about this before making a decision.",
            "This sounds promising. What's the next step?",
            "I have some questions about the contract terms.",
            "I'm looking for something more cost-effective.",
        ]

    def generate_transcript(self, duration_minutes: int = 5) -> str:
        """Generate a realistic call transcript"""
        transcript_lines = []

        # Generate conversation turns
        num_turns = random.randint(8, 15)

        for i in range(num_turns):
            if i % 2 == 0:  # Agent turn
                phrase = random.choice(self.agent_phrases)
                transcript_lines.append(f"Agent: {phrase}")
            else:  # Customer turn
                phrase = random.choice(self.customer_phrases)
                transcript_lines.append(f"Customer: {phrase}")

        return "\n".join(transcript_lines)

    def generate_call_data(self) -> Dict[str, Any]:
        """Generate complete call data"""
        start_time = fake.date_time_between(start_date="-30d", end_date="now")
        duration_seconds = random.randint(180, 900)  # 3-15 minutes
        transcript = self.generate_transcript(duration_minutes=duration_seconds // 60)

        # Simple calculations without AI
        lines = transcript.strip().split("\n")
        agent_words = 0
        total_words = 0
        for line in lines:
            if line.strip():
                if line.strip().startswith("Agent:"):
                    words = line.replace("Agent:", "").strip().split()
                    agent_words += len(words)
                total_words += len(line.split())

        agent_ratio = agent_words / total_words if total_words > 0 else 0.5

        # Simple sentiment calculation
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "love",
            "like",
            "happy",
            "satisfied",
            "perfect",
        ]
        negative_words = [
            "bad",
            "terrible",
            "hate",
            "dislike",
            "unhappy",
            "dissatisfied",
            "awful",
            "horrible",
        ]

        customer_text = " ".join(
            [
                line.replace("Customer:", "").strip()
                for line in lines
                if line.strip().startswith("Customer:")
            ]
        ).lower()
        positive_count = sum(1 for word in positive_words if word in customer_text)
        negative_count = sum(1 for word in negative_words if word in customer_text)
        total_sentiment_words = positive_count + negative_count
        sentiment_score = (
            (positive_count - negative_count) / total_sentiment_words
            if total_sentiment_words > 0
            else 0.0
        )
        sentiment_score = max(-1.0, min(1.0, sentiment_score))

        return {
            "call_id": f"CALL_{fake.unique.random_number(digits=8)}",
            "agent_id": f"AGENT_{fake.unique.random_number(digits=4)}",
            "customer_id": f"CUST_{fake.unique.random_number(digits=6)}",
            "language": "en",
            "start_time": start_time,
            "duration_seconds": duration_seconds,
            "transcript": transcript,
            "agent_talk_ratio": agent_ratio,
            "customer_sentiment_score": sentiment_score,
            "embedding": f"embedding_{random.randint(1000, 9999)}",  # Simple placeholder
        }


async def simple_ingestion_pipeline(num_calls: int = 200):
    """Run simplified ingestion pipeline"""
    generator = SimpleCallGenerator()
    calls = []

    async for db in get_async_db():
        print(f"Generating {num_calls} synthetic calls...")

        for i in range(num_calls):
            call_data = generator.generate_call_data()

            # Create call object
            call = Call(
                call_id=call_data["call_id"],
                agent_id=call_data["agent_id"],
                customer_id=call_data["customer_id"],
                language=call_data["language"],
                start_time=call_data["start_time"],
                duration_seconds=call_data["duration_seconds"],
                transcript=call_data["transcript"],
                agent_talk_ratio=call_data["agent_talk_ratio"],
                customer_sentiment_score=call_data["customer_sentiment_score"],
                embedding=call_data["embedding"],
            )

            calls.append(call)

            # Batch commit every 50 calls
            if (i + 1) % 50 == 0:
                db.add_all(calls)
                await db.commit()
                print(f"Inserted {i + 1} calls...")
                calls = []

        # Commit remaining calls
        if calls:
            db.add_all(calls)
            await db.commit()
            print(f"Inserted remaining {len(calls)} calls...")

        print("Data ingestion completed successfully!")
        break


async def main():
    """Main function to run the ingestion pipeline"""
    try:
        await simple_ingestion_pipeline(num_calls=200)
    except Exception as e:
        print(f"Error during data ingestion: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
