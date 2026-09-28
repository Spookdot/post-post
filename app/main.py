from tortoise.contrib.fastapi import RegisterTortoise, tortoise_exception_handlers
from tortoise.config import DBUrlConfig, AppConfig
from tortoise import TortoiseConfig
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from uuid import UUID, uuid4

from .models.tortoise import Post, User
from .models.pydantic import Post_Pydantic, Token_Pydantic, get_settings
from .auth import get_current_user, authenticate_user, generate_token, save_token_for_user

password_hash = PasswordHash.recommended()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    tortoise_config = TortoiseConfig(
        connections={"default": DBUrlConfig(settings.db_url)},
        apps={
            "models": AppConfig(
                models=["app.models.tortoise"],
                default_connection="default",
                migrations="migrations"
            )
        }
    )
    async with RegisterTortoise(app, config=tortoise_config, generate_schemas=True):
        # db connected
        username = settings.test_user_username
        password = settings.test_user_password
        if username and password:
            hashed_password = password_hash.hash(password)

            await User.create(username=username, password_hash=hashed_password)
        yield
        # app teardown
    # db connections closed

app = FastAPI(
    title="post-post",
    lifespan=lifespan,
    exception_handlers=tortoise_exception_handlers(),
)


@app.post("/token", response_model=Token_Pydantic)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # TODO Replace with actual Database use and password verification and return token
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    # Generate token
    token = generate_token()
    await save_token_for_user(user.username, token)

    return Token_Pydantic(access_token=token, token_type="bearer")


# Post management
@app.get("/post/{id}", response_model=Post_Pydantic, responses={404: {"model": str}})
async def get_post(id: UUID):
    item = await Post.get_or_none(id=id)
    if not item:
        return (status.HTTP_404_NOT_FOUND, "No post under this ID")
    return await Post_Pydantic.from_tortoise_orm(item)


@app.post("/post")
async def create_post(post: Post_Pydantic, _: Annotated[User, Depends(get_current_user)]) -> UUID:
    # TODO Use actual User data
    id = uuid4()
    tpost = await Post.create(id=id, **post.model_dump(exclude_none=True))
    await tpost.save()
    return id

