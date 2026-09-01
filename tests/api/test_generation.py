import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from app.main import app
from app.models.learning import ResearchSource, LearningContent
import uuid
import json

@pytest.fixture
def mock_openai(mocker):
    # Mock the OpenAI client module globally or locally where used
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chat.completions.create = mock_chat
    return mock_client, mock_chat

@pytest.fixture
def sample_research(db_session):
    research = ResearchSource(
        id=str(uuid.uuid4()),
        url="https://example.com/health",
        domain="example.com",
        source_type="INTERNET",
        title="PCOS Information",
        raw_content="PCOS is a common condition...",
        content_hash="mock_hash"
    )
    db_session.add(research)
    db_session.commit()
    db_session.refresh(research)
    return research

@pytest.fixture
def sample_article(db_session):
    article = LearningContent(
        id=str(uuid.uuid4()),
        title="Mock Article",
        content_type="ARTICLE",
        source_type="INTERNAL",
        category="menstrual-health",
        language="en",
        audience="ALL",
        status="DRAFT",
        body=[{"type": "text", "content": "Mock text"}],
        translation_group_id=str(uuid.uuid4())
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article

@pytest.mark.asyncio
async def test_generate_english_article(admin_token_headers, sample_research, mocker):
    mock_service = MagicMock()
    mock_service.generate_english_article.return_value = {
        "message": "Article generated successfully.",
        "content_id": "fake_id",
        "status": "DRAFT",
        "validation_issues": []
    }
    
    with patch("app.api.v1.endpoints.admin.get_generation_service", return_value=mock_service):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/admin/research/{sample_research.id}/generate",
                headers=admin_token_headers
            )
            
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"

@pytest.mark.asyncio
async def test_localize_article(admin_token_headers, sample_article, mocker):
    mock_service = MagicMock()
    mock_service.localize_article.return_value = {
        "message": "Localized to hi successfully.",
        "content_id": "fake_id_hi",
        "status": "DRAFT",
        "validation_issues": []
    }
    
    with patch("app.api.v1.endpoints.admin.get_generation_service", return_value=mock_service):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/admin/learning/{sample_article.id}/localize",
                json={"target_language": "hi"},
                headers=admin_token_headers
            )
            
    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"

@pytest.mark.asyncio
async def test_validate_article_failure(admin_token_headers, sample_article, mocker):
    mock_service = MagicMock()
    mock_service.validate_content.return_value = {
        "is_valid": False,
        "status": "NEEDS_REVIEW",
        "issues": ["Missing citation for statistic"]
    }
    
    with patch("app.api.v1.endpoints.admin.get_generation_service", return_value=mock_service):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/admin/learning/{sample_article.id}/validate",
                headers=admin_token_headers
            )
            
    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert response.json()["status"] == "NEEDS_REVIEW"
    assert "Missing citation" in response.json()["issues"][0]
