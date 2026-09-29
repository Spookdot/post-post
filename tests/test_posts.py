from pydantic import ValidationError
from app.models.pydantic import get_settings, Token_Pydantic, Settings
from uuid import uuid4
from tortoise.context import tortoise_test_context
from fastapi import status
from fastapi.testclient import TestClient
import pytest_asyncio
import pytest
import os
from app.models.tortoise import Post
from app.main import app

@pytest_asyncio.fixture
def settings():
    return get_settings()

@pytest_asyncio.fixture
async def db():
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(["app.models.tortoise"], db_url=db_url) as ctx:
        yield ctx

@pytest_asyncio.fixture
def client():
    with TestClient(app, base_url="http://localhost:8000") as client:
        yield client

@pytest.mark.asyncio
async def test_create_post(db):
    _ = db
    id = uuid4()
    title = "hello"
    content = "world"

    await Post.create(id=id, title=title, content=content)

    post_in_db = await Post.get(id=id)
    assert post_in_db.title == title
    assert post_in_db.content == content

@pytest.mark.asyncio
async def test_login(db, client: TestClient, settings: Settings):
    form_data = {
        "username": settings.test_user_username,
        "password": settings.test_user_password
    }
    response = client.post("/token", data=form_data)
    assert response.status_code == 200, response.text

    response_dict = response.json()

    token_data = Token_Pydantic(**response_dict)
    assert token_data.token_type == "bearer"
    assert len(token_data.access_token) == 64

@pytest.mark.asyncio
async def test_authorization(db, client: TestClient, settings: Settings):
    title = "hello"
    content = "world"
    post_json = {"title": title, "content": content}

    # Test that I cannnot make posts without logging in
    response = client.post("/post", json=post_json)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Test login endpoint
    form_data = {
        "username": settings.test_user_username,
        "password": settings.test_user_password
    }
    response = client.post("/token", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    token = response_json["access_token"]
    assert len(token) == 64

    # Test that I can now make posts
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK, response.text
    post_id = response.json()

    # check if the post was created and I can access it without Authorization
    response = client.get(f"/post/{post_id}")
    assert response.status_code != status.HTTP_401_UNAUTHORIZED
    assert response.status_code == status.HTTP_200_OK, response.text
    
@pytest.mark.asyncio
async def test_tags(db, client: TestClient, settings: Settings):
    title = "welcome to my blog"
    content = "This is my blog"
    tags = ["introduction", "personal"]
    post_json = {
        "title": title,
        "content": content,
        "tags": tags
    }

    # Log in
    form_data = {
        "username": settings.test_user_username,
        "password": settings.test_user_password
    }
    response = client.post("/token", data=form_data)
    response_json = response.json()
    token = response_json["access_token"]

    # Make a post with tags
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, "Unable to create post with tags"
    post_id = response.json()

    # Search for the post via tags
    response = client.get(f"/tag/{tags[0]}")
    assert response.status_code == 200, "Unable to search for posts using tags"
    posts = response.json()

    # Verify that any of the posts that were returned is actually the one we made
    assert any([i.id == post_id for i in posts])
