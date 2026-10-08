from sqlmodel import SQLModel, create_engine, StaticPool, Session, select
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.auth import hash_password
from app.dependencies import get_session, get_settings, Settings
from app.models import Post, TokenResponse, User, Tag, PostCreate, UserCreate, PostCreateReblog, PostPublic

@pytest.fixture(name="settings", scope="session")
def settings_fixture():
    return get_settings()

@pytest.fixture(name="session")
def session_fixture(settings: Settings):
    engine = create_engine(settings.db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def user_fixture(session: Session, settings: Settings) -> UserCreate:
    username = settings.test_user_username
    password = settings.test_user_password

    password_hash = hash_password(password)

    user = User(username=username, password_hash=password_hash)
    session.add(user)
    session.commit()
    return UserCreate(username=username, password=password)

@pytest.fixture(name="example_post")
def example_post_fixture() -> PostCreate:
    return PostCreate(
        title="welcome to my blog", 
        content="This is my blog",
        tags=["introduction", "personal"]
    )

def login(client: TestClient, user: UserCreate) -> TokenResponse:
    response = client.post("/token", data=user.model_dump())
    assert response.status_code == 200, response.text

    return TokenResponse.model_validate(response.json())


def test_create_post(session: Session, settings: Settings):
    id = uuid4()
    title = "hello"
    content = "world"
    username = settings.test_user_username

    post = Post(id=id, title=title, content=content, username=username)
    session.add(post)
    session.commit()
    session.refresh(post)

    assert post.id == id

    statement = select(Post).where(Post.id == id)
    results = session.exec(statement)
    post_in_db = results.one()

    assert post_in_db.title == title
    assert post_in_db.content == content
    assert post_in_db.username == username

def test_login(test_user: UserCreate, client: TestClient):
    token_data = login(client, test_user)
    assert token_data.token_type == "bearer"
    assert len(token_data.access_token) == 64

def test_authorization(client: TestClient, test_user: UserCreate):
    post = PostCreate(title="hello", content="world")
    post_json = post.model_dump()

    # Test that I cannnot make posts without logging in
    response = client.post("/post", json=post_json)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Test login endpoint
    token_data = login(client, test_user)
    token = token_data.access_token
    assert len(token) == 64

    # Test that I can now make posts
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK, response.text
    post_id = response.json()

    # check if the post was created and I can access it without Authorization
    response = client.get(f"/post/{post_id}")
    assert response.status_code != status.HTTP_401_UNAUTHORIZED
    assert response.status_code == status.HTTP_200_OK, response.text
    
def test_tags(session: Session, client: TestClient, test_user: UserCreate, example_post: PostCreate):
    post_json = example_post.model_dump()

    # Log in
    token_data = login(client, test_user)
    token = token_data.access_token

    # Make a post with tags
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, "Unable to create post with tags"
    post_id = response.json()
    
    # Check the post was actually created
    tag_in_db = Tag.fetch_optional(session, example_post.tags[0])
    assert tag_in_db is not None, "Tag is missing from database"

    # Search for the post via tags
    response = client.get(f"/tag/{example_post.tags[0]}")
    assert response.status_code == 200, "Unable to search for posts using tags"
    posts = response.json()
    
    # Verify that any of the posts that were returned is actually the one we made
    assert any([i["id"] == post_id for i in posts]), posts

def test_user_posts(client: TestClient, test_user: UserCreate, example_post: PostCreate):
    post_json = example_post.model_dump()

    token = login(client, test_user).access_token

    # Make a post
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, "Unable to create post"
    post_id = response.json()

    response = client.get(f"/user/{test_user.username}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, "Unable to find posts associated with the Test User"
    posts = response.json()

    assert any([i["id"] == post_id for i in posts]), posts

def test_post_delete(client: TestClient, test_user: UserCreate, example_post: PostCreate):
    post_json = example_post.model_dump()
    token = login(client, test_user).access_token

    # Create a Post
    response = client.post("/post", json=post_json, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, "Unable to create post"
    post_id = response.json()
    
    # Check that the post was created
    response = client.get(f"/post/{post_id}")
    assert response.status_code == status.HTTP_200_OK, response.text

    # Check that I cannot delete the post without Authorization
    response = client.delete(f"/post/{post_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    # Delete post
    response = client.delete(f"/post/{post_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK, response.text

    # Check that the post is now missing
    response = client.get(f"/post/{post_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text

def test_reblog_with_content(client: TestClient, test_user: UserCreate, example_post: PostCreate):
    # Log in
    token_data = login(client, test_user)
    token = token_data.access_token

    # Make a post
    response = client.post("/post", json=example_post.model_dump(mode="json"), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    reblog_id = response.json()

    # Create reblog with content
    post = PostCreateReblog(title="Addition", content="I think this", reblog=reblog_id)
    response = client.post("/post", json=post.model_dump(mode="json"), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    post_id = response.json()

    # Check the reblog actually worked
    response = client.get(f"/post/{post_id}")
    assert response.status_code == 200
    post_dict = response.json()
    assert post_dict is not None
    post = PostPublic.model_validate(post_dict)
    assert str(post.parent_id) == reblog_id

def test_reblog_without_content(client: TestClient, test_user: UserCreate, example_post: PostCreate):
    # Log in
    token_data = login(client, test_user)
    token = token_data.access_token

    # Make a post
    response = client.post("/post", json=example_post.model_dump(mode="json"), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    reblog_id = response.json()

    # Create reblog without content
    post = PostCreateReblog(reblog=reblog_id)
    response = client.post("/post", json=post.model_dump(mode="json"), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    post_id = response.json()

    # Check the reblog actually worked
    response = client.get(f"/post/{post_id}")
    assert response.status_code == 200
    post_dict = response.json()
    assert post_dict is not None
    post = PostPublic.model_validate(post_dict)
    assert str(post.parent_id) == reblog_id
