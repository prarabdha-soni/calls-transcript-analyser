import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker
import random
from app.ai_insights import analytics_processor
from app.models import Call
from sqlalchemy.ext.asyncio import AsyncSession


fake = Faker()


class CallTranscriptGenerator:
    """Generate synthetic call transcripts for testing"""
    
    def __init__(self):
        self.sales_topics = [
            "product demonstration", "pricing discussion", "objection handling",
            "closing techniques", "follow-up scheduling", "competitor comparison",
            "feature benefits", "customer needs analysis", "solution presentation"
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
            "Is there anything else you'd like to know?"
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
            "I'm looking for something more cost-effective."
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
        start_time = fake.date_time_between(
            start_date='-30d',
            end_date='now'
        )
        
        duration_seconds = random.randint(180, 900)  # 3-15 minutes
        
        return {
            "call_id": f"CALL_{fake.unique.random_number(digits=8)}",
            "agent_id": f"AGENT_{fake.unique.random_number(digits=4)}",
            "customer_id": f"CUST_{fake.unique.random_number(digits=6)}",
            "language": "en",
            "start_time": start_time,
            "duration_seconds": duration_seconds,
            "transcript": self.generate_transcript(duration_seconds // 60)
        }


class DataIngestionPipeline:
    """Async pipeline for ingesting call data"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.generator = CallTranscriptGenerator()
    
    async def ingest_calls(self, num_calls: int = 200) -> List[Call]:
        """Ingest synthetic call data"""
        calls = []
        
        for i in range(num_calls):
            call_data = self.generator.generate_call_data()
            
            # Process with AI insights
            agent_ratio, sentiment_score, embedding = analytics_processor.process(call_data["transcript"])
            
            # Create call object
            call = Call(
                call_id=call_data["call_id"],
                agent_id=call_data["agent_id"],
                customer_id=call_data["customer_id"],
                language=call_data["language"],
                start_time=call_data["start_time"],
                duration_seconds=call_data["duration_seconds"],
                transcript=call_data["transcript"],
                agent_talk_ratio=agent_ratio,
                customer_sentiment_score=sentiment_score,
                embedding=embedding
            )
            
            calls.append(call)
            
            # Batch commit every 50 calls
            if (i + 1) % 50 == 0:
                self.db_session.add_all(calls)
                await self.db_session.commit()
                calls = []
        
        # Commit remaining calls
        if calls:
            self.db_session.add_all(calls)
            await self.db_session.commit()
        
        return calls
    
    async def save_raw_data(self, calls: List[Call], output_dir: str = "raw_data"):
        """Save raw call data as JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        for call in calls:
            filename = f"{call.call_id}.json"
            filepath = os.path.join(output_dir, filename)
            
            call_data = {
                "call_id": call.call_id,
                "agent_id": call.agent_id,
                "customer_id": call.customer_id,
                "language": call.language,
                "start_time": call.start_time.isoformat(),
                "duration_seconds": call.duration_seconds,
                "transcript": call.transcript,
                "agent_talk_ratio": call.agent_talk_ratio,
                "customer_sentiment_score": call.customer_sentiment_score,
                "embedding": call.embedding
            }
            
            with open(filepath, 'w') as f:
                json.dump(call_data, f, indent=2)


async def run_ingestion_pipeline(db_session: AsyncSession, num_calls: int = 200):
    """Run the complete ingestion pipeline"""
    pipeline = DataIngestionPipeline(db_session)
    
    calls = await pipeline.ingest_calls(num_calls)
    
    await pipeline.save_raw_data(calls)
    
    return calls 