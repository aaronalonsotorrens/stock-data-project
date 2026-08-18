from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    """
    Check that the health endpoint is working and returns
    the response I expect.
    """

    # Using TestClient inside a context manager makes sure
    # FastAPI runs its startup and shutdown logic.
    with TestClient(app) as client:
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

    with TestClient(app) as client:
        response = client.get("/stocks/THISSHOULDNOTEXIST")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "No stored data found for THISSHOULDNOTEXIST"
    }


def test_homepage_loads():
    """
    Check that the simple HTML frontend loads successfully.
    """

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Apple Stock Data" in response.text