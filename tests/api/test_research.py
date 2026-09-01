import pytest
from httpx import AsyncClient
from app.main import app
from app.services.research_service import ResearchService

@pytest.mark.asyncio
async def test_ssrf_protection_localhost(admin_token_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/research/ingest",
            headers=admin_token_headers,
            json={"url": "http://127.0.0.1:8000"}
        )
    assert response.status_code == 403
    assert "internal/private IPs" in response.json()["detail"]

@pytest.mark.asyncio
async def test_ssrf_protection_aws_metadata(admin_token_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/research/ingest",
            headers=admin_token_headers,
            json={"url": "http://169.254.169.254/latest/meta-data/"}
        )
    assert response.status_code == 403
    assert "internal/private IPs" in response.json()["detail"]

@pytest.mark.asyncio
async def test_invalid_scheme(admin_token_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/research/ingest",
            headers=admin_token_headers,
            json={"url": "ftp://example.com"}
        )
    assert response.status_code == 400
    assert "Only HTTP and HTTPS" in response.json()["detail"]
