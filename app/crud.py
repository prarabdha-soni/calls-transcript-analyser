import json
from datetime import datetime
from typing import List, Optional

import numpy as np
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai_insights import analytics_processor
from app.models import Agent, Call, Customer
from app.schemas import CallQueryParams


class CallCRUD:
    @staticmethod
    async def create_call(db: AsyncSession, call_data: dict) -> Call:
        """Create a new call record"""
        call = Call(**call_data)
        db.add(call)
        await db.commit()
        await db.refresh(call)
        return call

    @staticmethod
    async def get_call(db: AsyncSession, call_id: str) -> Optional[Call]:
        """Get a call by ID"""
        result = await db.execute(select(Call).where(Call.call_id == call_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_calls(
        db: AsyncSession, params: CallQueryParams
    ) -> tuple[List[Call], int]:
        """Get calls with filtering and pagination"""
        query = select(Call)

        # Apply filters
        if params.agent_id:
            query = query.where(Call.agent_id == params.agent_id)

        if params.from_date:
            query = query.where(Call.start_time >= params.from_date)

        if params.to_date:
            query = query.where(Call.start_time <= params.to_date)

        if params.min_sentiment is not None:
            query = query.where(Call.customer_sentiment_score >= params.min_sentiment)

        if params.max_sentiment is not None:
            query = query.where(Call.customer_sentiment_score <= params.max_sentiment)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.offset(params.offset).limit(params.limit)

        # Execute query
        result = await db.execute(query)
        calls = result.scalars().all()

        return list(calls), total

    @staticmethod
    async def get_similar_calls(
        db: AsyncSession, call_id: str, limit: int = 5
    ) -> List[tuple[Call, float]]:
        """Find similar calls using cosine similarity"""
        # Get the target call
        target_call = await CallCRUD.get_call(db, call_id)
        if not target_call or not target_call.embedding:
            return []

        # Get all other calls with embeddings
        result = await db.execute(
            select(Call).where(
                and_(Call.id != target_call.id, Call.embedding.isnot(None))
            )
        )
        calls = result.scalars().all()

        # Calculate similarities
        similarities = []
        target_embedding = target_call.embedding

        for call in calls:
            if call.embedding:
                similarity = analytics_processor.cosine_similarity(
                    target_embedding, call.embedding
                )
                similarities.append((call, similarity))

        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    @staticmethod
    async def update_call_analytics(
        db: AsyncSession,
        call_id: str,
        agent_ratio: float,
        sentiment_score: float,
        embedding: str,
    ) -> Optional[Call]:
        """Update call with AI analytics"""
        call = await CallCRUD.get_call(db, call_id)
        if call:
            call.agent_talk_ratio = agent_ratio
            call.customer_sentiment_score = sentiment_score
            call.embedding = embedding
            await db.commit()
            await db.refresh(call)
        return call


class AgentCRUD:
    @staticmethod
    async def get_agent_analytics(db: AsyncSession) -> List[dict]:
        """Get analytics for all agents"""
        # Calculate agent statistics
        query = text(
            """
        SELECT 
            agent_id,
            COUNT(*) as total_calls,
            AVG(customer_sentiment_score) as avg_sentiment,
            AVG(agent_talk_ratio) as avg_talk_ratio
        FROM calls 
        WHERE agent_talk_ratio IS NOT NULL 
        AND customer_sentiment_score IS NOT NULL
        GROUP BY agent_id
        ORDER BY avg_sentiment DESC, total_calls DESC
        """
        )
        result = await db.execute(query)
        rows = result.fetchall()
        analytics = []
        for row in rows:
            analytics.append(
                {
                    "agent_id": row[0],
                    "name": f"Agent {row[0]}",  # In real app, get from agents table
                    "total_calls": row[1],
                    "avg_sentiment": float(row[2]) if row[2] else 0.0,
                    "avg_talk_ratio": float(row[3]) if row[3] else 0.0,
                }
            )
        return analytics


class CustomerCRUD:
    @staticmethod
    async def create_customer(db: AsyncSession, customer_data: dict) -> Customer:
        """Create a new customer record"""
        customer = Customer(**customer_data)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_customer(db: AsyncSession, customer_id: str) -> Optional[Customer]:
        """Get a customer by ID"""
        result = await db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        )
        return result.scalar_one_or_none()
