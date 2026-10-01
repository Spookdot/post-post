from sqlmodel import SQLModel, create_engine, StaticPool, Session, select
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
import pytest_asyncio
import pytest
import os

from app.main import app
from app.auth import hash_password
from app.dependencies import get_session, get_settings, Settings
from app.models.sqlmodel import Post, TokenResponse, User, Tag

@pytest.fixture(name="settings")
def settings_fixture():
    return get_settings()

@pytest.fixture(name="session")
def session_fixture(settings: Settings):
    engine = create_engine(settings.db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Create test user
        username = settings.test_user_username
        password = settings.test_user_password

        password_hash = hash_password(password)

        user = User(username=username, password_hash=password_hash)
        session.add(user)
        session.commit()

        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

def test_create_post(session: Session):
    id = uuid4()
    title = "hello"
    content = "world"

    post = Post(id=id, title=title, content=content)
    session.add(post)
    session.commit()
    session.refresh(post)

    assert post.id == id

    statement = select(Post).where(Post.id == id)
    results = session.exec(statement)
    post_in_db = results.one()

    assert post_in_db.title == title
    assert post_in_db.content == content

def test_login(client: TestClient, settings: Settings):
    form_data = {
        "username": settings.test_user_username,
        "password": settings.test_user_password
    }
    response = client.post("/token", data=form_data)
    assert response.status_code == 200, response.text

    response_dict = response.json()

    token_data = TokenResponse(**response_dict)
    assert token_data.token_type == "bearer"
    assert len(token_data.access_token) == 64

@pytest.mark.asyncio
async def test_authorization(client: TestClient, settings: Settings):
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
    
def test_tags(session: Session, client: TestClient, settings: Settings):
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
    
    # Check the post was actually created
    statement = select(Tag).where(Tag.name == tags[0])
    results = session.exec(statement)
    _ = results.one()

    # Search for the post via tags
    response = client.get(f"/tag/{tags[0]}")
    assert response.status_code == 200, "Unable to search for posts using tags"
    posts = response.json()
    
    # Verify that any of the posts that were returned is actually the one we made
    assert any([i["id"] == post_id for i in posts]), posts
