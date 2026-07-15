import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CommHub"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_root_serves_html(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
