import pytest
from fastapi.testclient import TestClient

from app.api import app


def test_health_check():
    """Test the health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_api_docs():
    """Test that API documentation is accessible."""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that OpenAPI schema is accessible."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


def test_app_import():
    """Test that the app can be imported without errors."""
    from app.api import app

    assert app is not None


def test_config_import():
    """Test that config can be imported without errors."""
    from app.config import settings

    assert settings is not None
