from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CallBase(BaseModel):
    call_id: str
    agent_id: str
    customer_id: str
    language: str = "en"
    start_time: datetime
    duration_seconds: int
    transcript: str


class CallCreate(CallBase):
    pass


class CallUpdate(BaseModel):
    agent_talk_ratio: Optional[float] = None
    customer_sentiment_score: Optional[float] = None
    embedding: Optional[str] = None


class Call(CallBase):
    id: str
    agent_talk_ratio: Optional[float] = None
    customer_sentiment_score: Optional[float] = None
    embedding: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    calls: List[Call]
    total: int
    limit: int
    offset: int


class CallRecommendation(BaseModel):
    call_id: str
    similarity_score: float
    transcript_preview: str


class CoachingNudge(BaseModel):
    title: str
    suggestion: str


class CallRecommendationsResponse(BaseModel):
    similar_calls: List[CallRecommendation]
    coaching_nudges: List[CoachingNudge]


class AgentAnalytics(BaseModel):
    agent_id: str
    name: str
    total_calls: int
    avg_sentiment: float
    avg_talk_ratio: float


class AgentAnalyticsResponse(BaseModel):
    agents: List[AgentAnalytics]


class CallQueryParams(BaseModel):
    limit: Optional[int] = Field(default=50, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)
    agent_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_sentiment: Optional[float] = Field(default=None, ge=-1, le=1)
    max_sentiment: Optional[float] = Field(default=None, ge=-1, le=1)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
