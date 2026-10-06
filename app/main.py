from sqlmodel import Session
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from uuid import UUID

from .models import create_db_and_tables, User, Post, TokenResponse, PostCreate, PostPublic, Tag, tags_from_strings, HTTPError, PostCreateReblog
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

get_responses: dict[int | str, dict[str, Any]] = {
    404: {"model": HTTPError}
}
post_responses: dict[int | str, dict[str, Any]] = {
    400: {"model": HTTPError}
}

UserDependency = Annotated[User, Depends(get_current_user)]
SessionDependency = Annotated[Session, Depends(get_session)]

@app.post("/token", response_model=TokenResponse, responses=post_responses)
def login(
    session: SessionDependency,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenResponse:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # Generate token
    token = generate_token()
    save_token_for_user(session, user.username, token)

    return TokenResponse(access_token=token, token_type="bearer")


# Post management
@app.get("/post/{id}", response_model=PostPublic, responses=get_responses)
def get_post(id: UUID, session: SessionDependency) -> PostPublic:
    item = Post.fetch_optional(session, id)
    if not item:
        raise HTTPException(404, "No post under this ID")
    
    tags = item.get_tags_as_str()
    post_public = item.into_convert().into_public(
        id=item.id,
        username=item.username,
        tags=tags,
        reblog_of_id=item.reblog_of_id
    )

    return post_public


@app.post("/post", response_model=UUID, responses=post_responses)
def create_post(post_create: PostCreateReblog | PostCreate, session: SessionDependency, user: UserDependency):
    post = post_create.into_convert().into_table(user)
    tags = tags_from_strings(post_create.tags)
    post.add_tags(tags)
    session.add(post)

    if reblog_of_id := post_create.reblog:
        if reblog_of := Post.fetch_optional(session, reblog_of_id):
            reblog_of.reblogs.append(post)
        else:
            raise HTTPException(400, "Post to be reblogged doesn't exist")

    session.commit()
    session.refresh(post)
    return post.id

@app.delete(
    "/post/{id}", 
    response_model=UUID, 
    responses={ 403: { "model": HTTPError }, **get_responses}
)
def delete_post(id: UUID, session: SessionDependency, user: UserDependency) -> UUID:
    if post := Post.fetch_optional(session, id):
        if not post.username == user.username:
            raise HTTPException(403, "This post is not yours")

        return_id = post.id
        session.delete(post)
        session.commit()
        return return_id
    raise HTTPException(404, "No post under this ID")

@app.get("/tag/{tag_name}", response_model=list[PostPublic], responses=get_responses)
def get_posts_by_tag(
    tag_name: str, 
    session: SessionDependency,
) -> list[PostPublic]:
    if tag := Tag.fetch_optional(session, tag_name):
        return list(map(Post.into_public, tag.posts))
    raise HTTPException(404, "No Posts with this Tag")

@app.get("/user/{username}", response_model=list[PostPublic], responses=get_responses)
def get_posts_by_user(
    username: str,
    session: SessionDependency,
) -> list[PostPublic]:
    if user := User.fetch_optional(session, username):
        return list(map(Post.into_public, user.posts))
    raise HTTPException(404, "No Posts by this User")
