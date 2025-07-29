"""
Optimized FastAPI application with performance enhancements
Includes caching, connection pooling, and performance monitoring.
"""

import time
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_async_db
from app.schemas import (
    CallListResponse, Call, CallRecommendationsResponse, 
    AgentAnalyticsResponse, ErrorResponse
)
from app.crud import CRUD
from app.performance import (
    cache_response, monitor_performance, performance_monitor,
    query_optimizer, pool_manager, cache_manager
)
from app.config import settings

# Initialize FastAPI app with performance optimizations
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add performance middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
async def startup_event():
    """Initialize performance components on startup"""
    # Initialize connection pool
    await pool_manager.initialize_pool(
        settings.database_url_async,
        pool_size=20,
        max_overflow=30
    )
    
    # Initialize cache manager
    await cache_manager.__aenter__()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup performance components on shutdown"""
    await cache_manager.__aexit__(None, None, None)


@app.middleware("http")
async def performance_middleware(request, call_next):
    """Middleware to monitor API performance"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record API call metrics
    performance_monitor.record_api_call(
        endpoint=str(request.url.path),
        method=request.method,
        duration=duration,
        status_code=response.status_code
    )
    
    # Add performance headers
    response.headers["X-Response-Time"] = str(duration)
    response.headers["X-Cache-Hit-Rate"] = str(performance_monitor.get_cache_hit_rate())
    
    return response


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "Sales Call Analytics API",
        "version": settings.version,
        "status": "healthy"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check with performance metrics"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "performance": {
            "cache_hit_rate": performance_monitor.get_cache_hit_rate(),
            "total_errors": performance_monitor.metrics["errors"],
            "api_calls": len(performance_monitor.metrics["api_calls"])
        }
    }


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Get performance metrics"""
    return performance_monitor.get_metrics()


@app.get(f"{settings.api_v1_prefix}/calls", 
         response_model=CallListResponse,
         tags=["Calls"])
@cache_response(ttl=60)  # Cache for 1 minute
@monitor_performance
async def get_calls_optimized(
    limit: int = Query(50, ge=1, le=100, description="Number of calls to return"),
    offset: int = Query(0, ge=0, description="Number of calls to skip"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_date: Optional[datetime] = Query(None, description="Filter by start date"),
    to_date: Optional[datetime] = Query(None, description="Filter by end date"),
    min_sentiment: Optional[float] = Query(None, ge=-1, le=1, description="Minimum sentiment score"),
    max_sentiment: Optional[float] = Query(None, ge=-1, le=1, description="Maximum sentiment score"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get calls with optimized query performance"""
    try:
        # Use optimized query
        result = await query_optimizer.optimize_calls_query(
            session=db,
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            from_date=from_date,
            to_date=to_date,
            min_sentiment=min_sentiment,
            max_sentiment=max_sentiment
        )
        
        return CallListResponse(**result)
        
    except Exception as e:
        performance_monitor.record_error("calls_query_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_v1_prefix}/calls/{{call_id}}", 
         response_model=Call,
         tags=["Calls"])
@cache_response(ttl=300)  # Cache for 5 minutes
@monitor_performance
async def get_call_optimized(
    call_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific call by ID with caching"""
    try:
        crud = CRUD()
        call = await crud.get_call_by_id(db, call_id)
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return call
        
    except HTTPException:
        raise
    except Exception as e:
        performance_monitor.record_error("call_detail_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_v1_prefix}/calls/{{call_id}}/recommendations", 
         response_model=CallRecommendationsResponse,
         tags=["Calls"])
@cache_response(ttl=600)  # Cache for 10 minutes
@monitor_performance
async def get_call_recommendations_optimized(
    call_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get call recommendations with optimized similarity search"""
    try:
        crud = CRUD()
        
        # Get the target call
        target_call = await crud.get_call_by_id(db, call_id)
        if not target_call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Get similar calls using optimized query
        similar_calls = await crud.get_similar_calls_optimized(
            db, target_call.embedding, limit=5
        )
        
        # Generate coaching nudges
        coaching_nudges = await crud.generate_coaching_nudges_optimized(
            db, target_call, similar_calls
        )
        
        return CallRecommendationsResponse(
            similar_calls=similar_calls,
            coaching_nudges=coaching_nudges
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_monitor.record_error("recommendations_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_v1_prefix}/analytics/agents", 
         response_model=AgentAnalyticsResponse,
         tags=["Analytics"])
@cache_response(ttl=300)  # Cache for 5 minutes
@monitor_performance
async def get_agent_analytics_optimized(
    db: AsyncSession = Depends(get_async_db)
):
    """Get agent analytics with optimized aggregation query"""
    try:
        # Use optimized analytics query
        analytics_data = await query_optimizer.optimize_analytics_query(db)
        
        return AgentAnalyticsResponse(agents=analytics_data)
        
    except Exception as e:
        performance_monitor.record_error("analytics_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.api_v1_prefix}/calls/bulk", 
          tags=["Calls"])
async def bulk_ingest_calls(
    calls_data: List[dict],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Bulk ingest calls with background processing"""
    try:
        crud = CRUD()
        
        # Process in background for better performance
        background_tasks.add_task(crud.bulk_create_calls, db, calls_data)
        
        return {
            "message": f"Started processing {len(calls_data)} calls in background",
            "status": "processing"
        }
        
    except Exception as e:
        performance_monitor.record_error("bulk_ingest_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(f"{settings.api_v1_prefix}/cache", tags=["Cache"])
async def clear_cache():
    """Clear all cached data"""
    try:
        deleted_keys = await cache_manager.delete_pattern("api:*")
        return {
            "message": f"Cleared {deleted_keys} cached items",
            "deleted_keys": deleted_keys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_v1_prefix}/performance", tags=["Monitoring"])
async def get_performance_stats():
    """Get detailed performance statistics"""
    metrics = performance_monitor.get_metrics()
    
    # Calculate additional stats
    total_api_calls = sum(
        metric["count"] for metric in metrics["api_calls"].values()
    )
    
    avg_response_time = 0
    if metrics["api_calls"]:
        total_time = sum(
            metric["total_time"] for metric in metrics["api_calls"].values()
        )
        avg_response_time = total_time / total_api_calls if total_api_calls > 0 else 0
    
    return {
        "total_api_calls": total_api_calls,
        "avg_response_time": avg_response_time,
        "cache_hit_rate": performance_monitor.get_cache_hit_rate(),
        "total_errors": metrics["errors"],
        "endpoint_stats": metrics["api_calls"],
        "query_stats": metrics["query_times"]
    } 