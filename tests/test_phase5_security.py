import pytest
from httpx import AsyncClient
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.auth import User
from app.models.learning import LearningContent, LearningProgress, LearningBookmark, Topic, Subtopic

# Setup fixture utilities (assuming standard pytest-asyncio and app integration)

@pytest.fixture
def test_topic(db: Session):
    topic = Topic(name="Phase 5 Topic", slug="phase-5-topic", description="Test topic")
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic

@pytest.fixture
def teen_user(db: Session):
    user = User(email=f"teen_{uuid4()}@test.com", password_hash="dummy", role="user", age=15)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def teen_user_token(client_token_factory, teen_user):
    return client_token_factory(teen_user)

@pytest.fixture
def adult_user(db: Session):
    user = User(email=f"adult_{uuid4()}@test.com", password_hash="dummy", role="user", age=25)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def adult_user_token(client_token_factory, adult_user):
    return client_token_factory(adult_user)

@pytest.fixture
def admin_user(db: Session):
    user = User(email=f"admin_{uuid4()}@test.com", password_hash="dummy", role="admin", age=30)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_user_token(client_token_factory, admin_user):
    return client_token_factory(admin_user)

@pytest.fixture
def adult_content(db: Session, admin_user: User, test_topic: Topic):
    content = LearningContent(
        author_id=admin_user.id,
        topic_id=test_topic.id,
        title="Adult Content",
        description="Only for adults",
        content_type="ARTICLE",
        source_type="ORIGINAL",
        status="PUBLISHED",
        audience="ADULT",
        language="en"
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content

@pytest.fixture
def draft_content(db: Session, admin_user: User, test_topic: Topic):
    content = LearningContent(
        author_id=admin_user.id,
        topic_id=test_topic.id,
        title="Draft Content",
        description="Draft",
        content_type="ARTICLE",
        source_type="ORIGINAL",
        status="DRAFT",
        audience="ALL",
        language="en"
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content

@pytest.mark.asyncio
async def test_teen_requesting_adult_article(
    async_client: AsyncClient, teen_user_token: dict, adult_content: LearningContent
):
    """Teen requesting adult article (Must 403 or exclude from feed)"""
    headers = {"Authorization": f"Bearer {teen_user_token['access_token']}"}
    response = await async_client.get(f"/api/v1/learning/{adult_content.id}", headers=headers)
    assert response.status_code == 403

    # Also test feed
    response = await async_client.get("/api/v1/learning", headers=headers)
    assert response.status_code == 200
    data = response.json()
    item_ids = [item["id"] for item in data["items"]]
    assert adult_content.id not in item_ids

@pytest.mark.asyncio
async def test_public_user_requesting_draft(
    async_client: AsyncClient, adult_user_token: dict, draft_content: LearningContent
):
    """Public user requesting DRAFT content (Must 404/403)"""
    headers = {"Authorization": f"Bearer {adult_user_token['access_token']}"}
    response = await async_client.get(f"/api/v1/learning/{draft_content.id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_normal_user_calling_admin_research(
    async_client: AsyncClient, adult_user_token: dict
):
    """Normal user calling admin research (Must 403)"""
    headers = {"Authorization": f"Bearer {adult_user_token['access_token']}"}
    response = await async_client.post("/api/v1/admin/research/analyze", json={"url": "https://example.com"}, headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_normal_user_calling_generation(
    async_client: AsyncClient, adult_user_token: dict, test_topic: Topic
):
    """Normal user calling AI generation (Must 403)"""
    headers = {"Authorization": f"Bearer {adult_user_token['access_token']}"}
    response = await async_client.post("/api/v1/admin/learning/generate", json={
        "topic_id": test_topic.id,
        "audience": "ALL",
        "language": "en",
        "focus_areas": "None"
    }, headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_user_requesting_another_users_history(
    async_client: AsyncClient, adult_user_token: dict, teen_user_token: dict, adult_user: User, teen_user: User, adult_content: LearningContent, db: Session
):
    """User requesting another user's history (Must isolate)"""
    # Create history for adult user
    progress = LearningProgress(user_id=adult_user.id, content_id=adult_content.id, view_count=1)
    db.add(progress)
    db.commit()
    
    # Teen requests history, should not see adult's history
    headers = {"Authorization": f"Bearer {teen_user_token['access_token']}"}
    response = await async_client.get("/api/v1/learning/history", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_user_requesting_another_users_bookmarks(
    async_client: AsyncClient, adult_user_token: dict, teen_user_token: dict, adult_user: User, teen_user: User, adult_content: LearningContent, db: Session
):
    """User requesting another user's bookmarks (Must isolate)"""
    bookmark = LearningBookmark(user_id=adult_user.id, content_id=adult_content.id)
    db.add(bookmark)
    db.commit()

    headers = {"Authorization": f"Bearer {teen_user_token['access_token']}"}
    response = await async_client.get("/api/v1/learning/bookmarks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_ssrf_invalid_source_url(
    async_client: AsyncClient, admin_user_token: dict
):
    """SSRF invalid source URL check"""
    headers = {"Authorization": f"Bearer {admin_user_token['access_token']}"}
    
    # Try localhost
    response = await async_client.post("/api/v1/admin/research/analyze", json={"url": "http://127.0.0.1:8000"}, headers=headers)
    assert response.status_code == 403
    assert "internal/private IPs" in response.text
    
    # Try invalid scheme
    response = await async_client.post("/api/v1/admin/research/analyze", json={"url": "file:///etc/passwd"}, headers=headers)
    assert response.status_code == 400
    assert "Invalid URL scheme" in response.text

@pytest.mark.asyncio
async def test_related_content_restrictions(
    async_client: AsyncClient, teen_user_token: dict, adult_content: LearningContent, admin_user: User, test_topic: Topic, db: Session
):
    """Related content should restrict adult content from teens."""
    # Create a teen content to serve as base
    teen_content = LearningContent(
        author_id=admin_user.id,
        topic_id=test_topic.id,
        title="Teen Content",
        description="For teens",
        content_type="ARTICLE",
        source_type="ORIGINAL",
        status="PUBLISHED",
        audience="TEEN",
        language="en"
    )
    db.add(teen_content)
    db.commit()
    db.refresh(teen_content)
    
    # Teen requests related content for teen_content. Adult content should not be in there.
    headers = {"Authorization": f"Bearer {teen_user_token['access_token']}"}
    response = await async_client.get(f"/api/v1/learning/{teen_content.id}/related", headers=headers)
    assert response.status_code == 200
    data = response.json()
    item_ids = [item["id"] for item in data["items"]]
    assert adult_content.id not in item_ids
