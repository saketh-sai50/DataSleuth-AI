def test_health_check(client) -> None:
    """
    Test that the health check endpoint returns 200 OK and reports
    both the API and SQLite database as healthy and connected.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
