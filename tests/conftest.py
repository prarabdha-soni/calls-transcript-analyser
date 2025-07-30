import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base
from app.api import app
from app.config import settings


# Always use SQLite for testing to avoid database connection issues
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_call_data():
    """Sample call data for testing."""
    return {
        "call_id": "TEST_CALL_001",
        "agent_id": "AGENT_001",
        "customer_id": "CUST_001",
        "language": "en",
        "start_time": "2024-01-01T10:00:00",
        "duration_seconds": 300,
        "transcript": "Agent: Hello, how can I help you today?\nCustomer: I'm interested in your product.\nAgent: Great! Let me tell you about our features."
    }


@pytest.fixture
def sample_calls():
    """Multiple sample calls for testing."""
    return [
        {
            "call_id": "TEST_CALL_001",
            "agent_id": "AGENT_001",
            "customer_id": "CUST_001",
            "language": "en",
            "start_time": "2024-01-01T10:00:00",
            "duration_seconds": 300,
            "transcript": "Agent: Hello, how can I help you today?\nCustomer: I'm interested in your product.\nAgent: Great! Let me tell you about our features."
        },
        {
            "call_id": "TEST_CALL_002",
            "agent_id": "AGENT_002",
            "customer_id": "CUST_002",
            "language": "en",
            "start_time": "2024-01-01T11:00:00",
            "duration_seconds": 450,
            "transcript": "Agent: Thank you for calling.\nCustomer: I have some questions about pricing.\nAgent: I'd be happy to discuss our pricing options."
        }
    ]
