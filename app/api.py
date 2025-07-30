from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json
import random
import asyncio
from datetime import datetime

from app.database import get_async_db
from app.crud import CallCRUD, AgentCRUD
from app.schemas import (
    Call,
    CallListResponse,
    CallRecommendationsResponse,
    CallRecommendation,
    CoachingNudge,
    AgentAnalyticsResponse,
    CallQueryParams,
    ErrorResponse,
)
from app.auth.models import TokenData
from app.config import settings
from app.auth.routes import router as auth_router
from app.auth.dependencies import get_current_user

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_router)


@app.get("/api/v1/calls", response_model=CallListResponse)
async def get_calls(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_sentiment: Optional[float] = Query(None, ge=-1, le=1),
    max_sentiment: Optional[float] = Query(None, ge=-1, le=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get calls with filtering and pagination"""
    try:
        # Parse date strings if provided
        from_dt = None
        to_dt = None

        if from_date:
            from_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        if to_date:
            to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))

        params = CallQueryParams(
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            from_date=from_dt,
            to_date=to_dt,
            min_sentiment=min_sentiment,
            max_sentiment=max_sentiment,
        )

        calls, total = await CallCRUD.get_calls(db, params)

        return CallListResponse(calls=calls, total=total, limit=limit, offset=offset)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving calls: {str(e)}")


@app.get("/api/v1/calls/{call_id}", response_model=Call)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific call by ID"""
    call = await CallCRUD.get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=404, detail=f"Call with ID {call_id} not found")
    return call


@app.get(
    "/api/v1/calls/{call_id}/recommendations",
    response_model=CallRecommendationsResponse,
)
async def get_call_recommendations(
    call_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get similar calls and coaching recommendations"""
    # Check if call exists
    call = await CallCRUD.get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=404, detail=f"Call with ID {call_id} not found")

    # Get similar calls
    similar_calls = await CallCRUD.get_similar_calls(db, call_id, limit=5)

    # Format similar calls
    recommendations = []
    for call_obj, similarity in similar_calls:
        # Get transcript preview (first 100 chars)
        preview = (
            call_obj.transcript[:100] + "..."
            if len(call_obj.transcript) > 100
            else call_obj.transcript
        )

        recommendations.append(
            CallRecommendation(
                call_id=call_obj.call_id,
                similarity_score=similarity,
                transcript_preview=preview,
            )
        )

    # Generate coaching nudges (simplified - in real app, use LLM)
    coaching_nudges = [
        CoachingNudge(
            title="Active Listening",
            suggestion="Practice active listening by summarizing customer concerns before responding.",
        ),
        CoachingNudge(
            title="Solution Focus",
            suggestion="Focus on providing solutions rather than just explaining features.",
        ),
        CoachingNudge(
            title="Closing Technique",
            suggestion="Use assumptive closing techniques to guide the conversation toward a positive outcome.",
        ),
    ]

    return CallRecommendationsResponse(
        similar_calls=recommendations, coaching_nudges=coaching_nudges
    )


@app.get("/api/v1/analytics/agents", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get agent analytics leaderboard"""
    try:
        analytics = await AgentCRUD.get_agent_analytics(db)

        return AgentAnalyticsResponse(agents=analytics)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving agent analytics: {str(e)}"
        )


@app.websocket("/ws/sentiment/{call_id}")
async def websocket_sentiment(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for real-time sentiment streaming"""
    await websocket.accept()

    try:
        # Simulate real-time sentiment updates
        while True:
            # Generate random sentiment score between -1 and 1
            sentiment = random.uniform(-1, 1)

            # Send sentiment data
            await websocket.send_text(
                json.dumps(
                    {
                        "call_id": call_id,
                        "sentiment": sentiment,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )

            # Wait 2 seconds before next update
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sales-call-analytics"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sales Call Analytics API",
        "version": settings.version,
        "docs": "/docs",
    }
