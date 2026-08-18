from fastapi.testclient import TestClient

from app.main import app


# TestClient lets me call the FastAPI endpoints directly in the tests
# without needing to manually start the Uvicorn server.
client = TestClient(app)


def test_health_endpoint():
    """
    Check that the health endpoint is working and returns
    the response I expect.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


def test_unknown_ticker_returns_404():
    """
    Check that the API gives a clear 404 response when
    there is no stored data for a ticker.
    """

    response = client.get("/stocks/THISSHOULDNOTEXIST")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "No stored data found for THISSHOULDNOTEXIST"
    }


def test_homepage_loads():
    """
    Check that the simple HTML frontend loads successfully.
    """

    response = client.get("/")

    assert response.status_code == 200

    # Check for something we know should appear on the page.
    assert "Apple Stock Data" in response.text