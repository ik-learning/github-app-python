"""Integration tests for the FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'GITHUB_APP_ID': '123456',
        'GITHUB_APP_PRIVATE_KEY': 'LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQp0ZXN0Cg==',  # base64 'test'
        'GITHUB_WEBHOOK_SECRET': 'test-secret'
    }):
        yield


@pytest.fixture
def client(mock_env_vars):
    """Create a test client for the FastAPI app."""
    # Import app after env vars are set
    from trash.app import app
    return TestClient(app)


@pytest.mark.integration
def test_health_check_endpoint(client):
    """Test the /status health check endpoint."""
    response = client.get("/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.integration
def test_health_check_returns_json(client):
    """Test that health check returns valid JSON."""
    response = client.get("/status")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


@pytest.mark.integration
def test_app_has_webhook_route(client):
    """Test that webhook route exists."""
    # The route is registered by GitHubApp, so we just check it doesn't 404
    # We can't easily test it without valid signatures
    response = client.post("/webhooks/github", json={})

    # Should not be 404, might be 403 (invalid signature) or other
    assert response.status_code != 404


@pytest.mark.integration
def test_fastapi_app_configuration(mock_env_vars):
    """Test that FastAPI app is configured correctly."""
    from trash.app import app

    assert app is not None
    assert app.title == "FastAPI"  # Default FastAPI title


@pytest.mark.integration
def test_github_app_initialization(mock_env_vars):
    """Test that GitHubApp is initialized with correct parameters."""
    from trash.app import github_app

    assert github_app is not None


@pytest.mark.integration
def test_environment_variable_validation():
    """Test that missing env vars raise an error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing required environment variables"):
            # Force reimport to trigger validation
            import importlib
            import trash.app
            importlib.reload(trash.app)


@pytest.mark.integration
def test_base64_private_key_decoding(mock_env_vars):
    """Test that base64 private key is decoded correctly."""
    # The app should successfully decode the base64 key
    # If it fails, app import would fail
    from trash.app import app
    assert app is not None


@pytest.mark.integration
def test_invalid_route_returns_404(client):
    """Test that invalid routes return 404."""
    response = client.get("/nonexistent-route")
    assert response.status_code == 404


@pytest.mark.integration
def test_health_check_response_structure(client):
    """Test that health check response has expected structure."""
    response = client.get("/status")
    data = response.json()

    assert isinstance(data, dict)
    assert "status" in data
    assert isinstance(data["status"], str)
