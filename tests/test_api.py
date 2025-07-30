import pytest
from fastapi.testclient import TestClient
from app.api import app
from app.crud import CallCRUD
from app.models import Call
from datetime import datetime


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sales-call-analytics"

    def test_get_calls_empty(self, client: TestClient):
        """Test getting calls when database is empty"""
        response = client.get("/api/v1/calls")
        assert response.status_code == 200
        data = response.json()
        assert data["calls"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_get_calls_with_filters(self, client: TestClient):
        """Test getting calls with various filters"""
        # Test with agent_id filter
        response = client.get("/api/v1/calls?agent_id=AGENT_001")
        assert response.status_code == 200

        # Test with date filters
        response = client.get(
            "/api/v1/calls?from_date=2024-01-01T00:00:00&to_date=2024-01-02T00:00:00"
        )
        assert response.status_code == 200

        # Test with sentiment filters
        response = client.get("/api/v1/calls?min_sentiment=-0.5&max_sentiment=0.5")
        assert response.status_code == 200

        # Test with pagination
        response = client.get("/api/v1/calls?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    def test_get_call_not_found(self, client: TestClient):
        """Test getting a call that doesn't exist"""
        response = client.get("/api/v1/calls/NONEXISTENT_CALL")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_get_call_recommendations_not_found(self, client: TestClient):
        """Test getting recommendations for a call that doesn't exist"""
        response = client.get("/api/v1/calls/NONEXISTENT_CALL/recommendations")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_get_agent_analytics(self, client: TestClient):
        """Test getting agent analytics"""
        response = client.get("/api/v1/analytics/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)


class TestDataValidation:
    """Test data validation"""

    def test_invalid_limit_parameter(self, client: TestClient):
        """Test invalid limit parameter"""
        response = client.get("/api/v1/calls?limit=0")
        assert response.status_code == 422

        response = client.get("/api/v1/calls?limit=101")
        assert response.status_code == 422

    def test_invalid_offset_parameter(self, client: TestClient):
        """Test invalid offset parameter"""
        response = client.get("/api/v1/calls?offset=-1")
        assert response.status_code == 422

    def test_invalid_sentiment_parameters(self, client: TestClient):
        """Test invalid sentiment parameters"""
        response = client.get("/api/v1/calls?min_sentiment=1.5")
        assert response.status_code == 422

        response = client.get("/api/v1/calls?max_sentiment=-1.5")
        assert response.status_code == 422


class TestWebSocket:
    """Test WebSocket functionality"""

    def test_websocket_sentiment(self, client: TestClient):
        """Test WebSocket sentiment streaming"""
        with client.websocket_connect("/ws/sentiment/TEST_CALL_001") as websocket:
            # Receive first message
            data = websocket.receive_text()
            import json

            message = json.loads(data)

            assert "call_id" in message
            assert "sentiment" in message
            assert "timestamp" in message
            assert message["call_id"] == "TEST_CALL_001"
            assert isinstance(message["sentiment"], (int, float))
            assert -1 <= message["sentiment"] <= 1


class TestCRUDOperations:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_call(self, test_session):
        """Test creating a call"""
        call_data = {
            "call_id": "TEST_CALL_001",
            "agent_id": "AGENT_001",
            "customer_id": "CUST_001",
            "language": "en",
            "start_time": datetime.now(),
            "duration_seconds": 300,
            "transcript": "Test transcript",
        }

        call = await CallCRUD.create_call(test_session, call_data)
        assert call.call_id == "TEST_CALL_001"
        assert call.agent_id == "AGENT_001"
        assert call.customer_id == "CUST_001"

    @pytest.mark.asyncio
    async def test_get_call(self, test_session):
        """Test getting a call"""
        # First create a call
        call_data = {
            "call_id": "TEST_CALL_002",
            "agent_id": "AGENT_002",
            "customer_id": "CUST_002",
            "language": "en",
            "start_time": datetime.now(),
            "duration_seconds": 300,
            "transcript": "Test transcript",
        }

        created_call = await CallCRUD.create_call(test_session, call_data)

        # Then retrieve it
        retrieved_call = await CallCRUD.get_call(test_session, "TEST_CALL_002")
        assert retrieved_call is not None
        assert retrieved_call.call_id == "TEST_CALL_002"

    @pytest.mark.asyncio
    async def test_get_call_not_found(self, test_session):
        """Test getting a call that doesn't exist"""
        call = await CallCRUD.get_call(test_session, "NONEXISTENT_CALL")
        assert call is None
