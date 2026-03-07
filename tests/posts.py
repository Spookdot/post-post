from uuid import uuid4
from tortoise.context import tortoise_test_context
from fastapi import status
from fastapi.testclient import TestClient
import pytest_asyncio
import pytest
import os
from models.tortoise import Post
from main import app

@pytest_asyncio.fixture
async def db():
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(["models.tortoise"], db_url=db_url) as ctx:
        yield ctx

@pytest_asyncio.fixture
def client():
    with TestClient(app, base_url="http://localhost:8000") as client:
        yield client

@pytest.mark.asyncio
async def test_create_post(db):
    id = uuid4()
    title = "hello"
    content = "world"

    post = await Post.create(id=id, title=title, content=content)
    await post.save()

    post_in_db = await Post.get(id=id)
    assert post_in_db.title == title
    assert post_in_db.content == content

@pytest.mark.asyncio
async def test_login(db, client: TestClient):
    response = client.post("/token", data={"username": "springjordan", "password": "1234"})
    assert len(response.json()["access_token"]) == 64

@pytest.mark.asyncio
async def test_authorization(db, client: TestClient):
    title = "hello"
    content = "world"
    post_json = {"title": title, "content": content}

    # Test that I cannnot make posts without logging in
    response = client.post("/post", json=post_json)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Test login endpoint
    response = client.post("/token", data={"username": "springjordan", "password": "1234"})
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    token = response_json["access_token"]
    assert len(token) == 64

    # Test that I can now make posts
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK
    post_id = response.text

    # check if the post was created and I can access it without Authorization
    response = client.get(f"/post/{post_id}")
    assert response.status_code != status.HTTP_401_UNAUTHORIZED
    assert response.status_code == status.HTTP_200_OK
    
