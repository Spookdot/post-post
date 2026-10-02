from sqlmodel import Session
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from uuid import UUID

from .models import create_db_and_tables, User, Post, TokenResponse, PostCreate, PostPublic, Tag, tags_from_strings
from .dependencies import get_engine, get_session
from .auth import get_current_user, authenticate_user, generate_token, save_token_for_user

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    engine = get_engine()
    create_db_and_tables(engine)
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
    item = Post.fetch_optional(session, id)
    if not item:
        return (status.HTTP_404_NOT_FOUND, "No post under this ID")
    
    post_public = PostPublic.model_validate(item)
    tags = item.get_tags_as_str()
    post_public.tags.extend(tags)

    return post_public


@app.post("/post")
def create_post(
    post_create: PostCreate, 
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)]
) -> UUID:
    post = post_create.into_convert().into_table(user)
    tags = tags_from_strings(post_create.tags)
    post.add_tags(tags)

    session.add(post)
    session.commit()
    session.refresh(post)
    return post.id


@app.get("/tag/{tag_name}", response_model=list[PostPublic])
def get_posts_by_tag(
    tag_name: str, 
    session: Annotated[Session, Depends(get_session)],
):
    if tag := Tag.fetch_optional(session, tag_name):
     return list(map(Post.into_public, tag.posts))
    return []

@app.get("/user/{username}", response_model=list[PostPublic])
def get_posts_by_user(
    username: str,
    session: Annotated[Session, Depends(get_session)],
):
    if user := User.fetch_optional(session, username):
        return list(map(Post.into_public, user.posts))
    return []
