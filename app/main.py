from sqlmodel import select, Session
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from uuid import UUID

from .models.sqlmodel import create_db_and_tables, User, Post, TokenResponse, PostCreate, PostPublic, Tag
from .dependencies import get_settings, get_engine, get_session
from .auth import get_current_user, authenticate_user, generate_token, save_token_for_user, hash_password

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    engine = get_engine()
    username = settings.test_user_username
    password = settings.test_user_password

    create_db_and_tables(engine)
    if username and password:
        hashed_password = hash_password(password)
        with Session(engine) as session:
            test_user = User(username=username, password_hash=hashed_password)
            session.add(test_user)
            session.commit()
    yield
    # app teardown

app = FastAPI(
    title="post-post",
    lifespan=lifespan,
)


@app.post("/token", response_model=TokenResponse)
def login(
    session: Annotated[Session, Depends(get_session)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # TODO Replace with actual Database use and password verification and return token
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    # Generate token
    token = generate_token()
    save_token_for_user(session, user.username, token)

    return TokenResponse(access_token=token, token_type="bearer")


# Post management
@app.get("/post/{id}", response_model=PostPublic, responses={404: {"model": str}})
def get_post(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
):
    statement = select(Post).where(Post.id == id)
    results = session.exec(statement)
    item = results.one_or_none()
    if not item:
        return (status.HTTP_404_NOT_FOUND, "No post under this ID")
    
    post_public = PostPublic(id=item.id, title=item.title, content=item.content)
    for tag in item.tags:
        post_public.tags.append(tag.name)

    return post_public


@app.post("/post")
def create_post(
    post_create: PostCreate, 
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)]
) -> UUID:
    # TODO Use actual User data
    post_dict = post_create.model_dump()
    tags = []
    for tag in post_dict["tags"]:
        tag_in_db = Tag(name=tag)
        tags.append(tag_in_db)

    post_dict["tags"] = tags

    post = Post.model_validate(post_dict)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post.id

