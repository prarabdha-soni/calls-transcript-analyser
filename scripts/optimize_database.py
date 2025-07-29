#!/usr/bin/env python3
"""
Database Optimization Script
Adds performance indexes and optimizes database for high load.
"""

import asyncio
import sys
import os
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import engine, async_engine


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    def __init__(self):
        self.engine = engine
        self.async_engine = async_engine
    
    async def create_performance_indexes(self):
        """Create performance indexes for better query performance"""
        print("Creating performance indexes...")
        
        indexes = [
            # Composite index for common query patterns
            """
            CREATE INDEX IF NOT EXISTS idx_calls_agent_date 
            ON calls (agent_id, start_time DESC)
            """,
            
            # Index for sentiment filtering
            """
            CREATE INDEX IF NOT EXISTS idx_calls_sentiment 
            ON calls (customer_sentiment_score)
            """,
            
            # Index for duration filtering
            """
            CREATE INDEX IF NOT EXISTS idx_calls_duration 
            ON calls (duration_seconds)
            """,
            
            # Index for language filtering
            """
            CREATE INDEX IF NOT EXISTS idx_calls_language 
            ON calls (language)
            """,
            
            # Composite index for analytics queries
            """
            CREATE INDEX IF NOT EXISTS idx_calls_analytics 
            ON calls (agent_id, customer_sentiment_score, agent_talk_ratio)
            """,
            
            # Partial index for active calls (recent calls)
            """
            CREATE INDEX IF NOT EXISTS idx_calls_recent 
            ON calls (start_time DESC) 
            WHERE start_time > CURRENT_DATE - INTERVAL '30 days'
            """,
            
            # Index for embedding similarity searches
            """
            CREATE INDEX IF NOT EXISTS idx_calls_embedding_gin 
            ON calls USING gin (embedding gin_trgm_ops)
            """,
            
            # Index for full-text search on transcript
            """
            CREATE INDEX IF NOT EXISTS idx_calls_transcript_fts 
            ON calls USING gin (to_tsvector('english', transcript))
            """
        ]
        
        async with self.async_engine.begin() as conn:
            for i, index_sql in enumerate(indexes, 1):
                try:
                    await conn.execute(text(index_sql))
                    print(f"Created index {i}/{len(indexes)}")
                except Exception as e:
                    print(f"Warning: Could not create index {i}: {e}")
    
    async def analyze_tables(self):
        """Run ANALYZE on tables to update statistics"""
        print("Analyzing tables...")
        
        async with self.async_engine.begin() as conn:
            await conn.execute(text("ANALYZE calls"))
            await conn.execute(text("ANALYZE agents"))
            await conn.execute(text("ANALYZE customers"))
        
        print("Table analysis completed")
    
    async def vacuum_tables(self):
        """Run VACUUM on tables to reclaim space and update statistics"""
        print("Running VACUUM...")
        
        # VACUUM cannot run inside a transaction block, so we need to use autocommit
        async with self.async_engine.connect() as conn:
            await conn.execute(text("VACUUM ANALYZE calls"))
            await conn.execute(text("VACUUM ANALYZE agents"))
            await conn.execute(text("VACUUM ANALYZE customers"))
        
        print("VACUUM completed")
    
    async def optimize_connection_pool(self):
        """Optimize connection pool settings"""
        print("Optimizing connection pool...")
        
        # These settings should be applied in the database configuration
        pool_settings = {
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_pre_ping": True,
            "pool_recycle": 3600
        }
        
        print(f"Recommended pool settings: {pool_settings}")
    
    async def create_materialized_views(self):
        """Create materialized views for frequently accessed data"""
        print("Creating materialized views...")
        
        views = [
            # Materialized view for agent analytics
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_agent_analytics AS
            SELECT 
                agent_id,
                COUNT(*) as total_calls,
                AVG(customer_sentiment_score) as avg_sentiment,
                AVG(agent_talk_ratio) as avg_talk_ratio,
                AVG(duration_seconds) as avg_duration,
                MIN(start_time) as first_call,
                MAX(start_time) as last_call,
                COUNT(CASE WHEN customer_sentiment_score > 0 THEN 1 END) as positive_calls,
                COUNT(CASE WHEN customer_sentiment_score < 0 THEN 1 END) as negative_calls
            FROM calls
            GROUP BY agent_id
            """,
            
            # Materialized view for daily call statistics
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_stats AS
            SELECT 
                DATE(start_time) as call_date,
                COUNT(*) as total_calls,
                AVG(duration_seconds) as avg_duration,
                AVG(customer_sentiment_score) as avg_sentiment,
                COUNT(DISTINCT agent_id) as unique_agents
            FROM calls
            GROUP BY DATE(start_time)
            """
        ]
        
        async with self.async_engine.begin() as conn:
            for i, view_sql in enumerate(views, 1):
                try:
                    await conn.execute(text(view_sql))
                    print(f"Created materialized view {i}/{len(views)}")
                except Exception as e:
                    print(f"Warning: Could not create view {i}: {e}")
    
    async def create_refresh_functions(self):
        """Create functions to refresh materialized views"""
        print("Creating refresh functions...")
        
        refresh_function = """
        CREATE OR REPLACE FUNCTION refresh_materialized_views()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_analytics;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        async with self.async_engine.begin() as conn:
            try:
                await conn.execute(text(refresh_function))
                print("Created refresh function")
            except Exception as e:
                print(f"Warning: Could not create refresh function: {e}")
    
    async def optimize_postgres_settings(self):
        """Suggest PostgreSQL configuration optimizations"""
        print("PostgreSQL optimization suggestions:")
        
        suggestions = [
            "shared_buffers = 256MB",
            "effective_cache_size = 1GB",
            "work_mem = 4MB",
            "maintenance_work_mem = 64MB",
            "checkpoint_completion_target = 0.9",
            "wal_buffers = 16MB",
            "default_statistics_target = 100",
            "random_page_cost = 1.1",
            "effective_io_concurrency = 200"
        ]
        
        for suggestion in suggestions:
            print(f"  {suggestion}")
    
    async def run_all_optimizations(self):
        """Run all database optimizations"""
        print("Starting database optimization...")
        
        try:
            await self.create_performance_indexes()
            await self.analyze_tables()
            await self.vacuum_tables()
            await self.optimize_connection_pool()
            await self.create_materialized_views()
            await self.create_refresh_functions()
            await self.optimize_postgres_settings()
            
            print("\nDatabase optimization completed successfully!")
            
        except Exception as e:
            print(f"Error during optimization: {e}")
            raise


async def main():
    """Main function to run database optimization"""
    optimizer = DatabaseOptimizer()
    await optimizer.run_all_optimizations()


if __name__ == "__main__":
    asyncio.run(main()) 