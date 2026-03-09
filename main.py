from tortoise.contrib.fastapi import RegisterTortoise, tortoise_exception_handlers
from dotenv import load_dotenv
from tortoise.config import DBUrlConfig, AppConfig
from tortoise import TortoiseConfig
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from uuid import UUID, uuid4
import os
import secrets

from models.tortoise import Post, User, Token
from models.pydantic import Post_Pydantic, User_Pydantic, Token_Pydantic

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    tortoise_config = TortoiseConfig(
        connections={"default": DBUrlConfig(os.environ["DB_URL"])},
        apps={
            "models": AppConfig(
                models=["models.tortoise"],
                default_connection="default",
                migrations="migrations"
            )
        }
    )
    async with RegisterTortoise(app, config=tortoise_config, generate_schemas=True):
        # db connected
        if os.environ.get("TEST_USER_USERNAME") and os.environ.get("TEST_USER_PASSWORD_HASH"):
            test_user = await User.create(
                username=os.environ["TEST_USER_USERNAME"], 
                password_hash=os.environ["TEST_USER_PASSWORD_HASH"]
            )
            await test_user.save()
        yield
        # app teardown
    # db connections closed

app = FastAPI(
    title="post-post",
    lifespan=lifespan,
    exception_handlers=tortoise_exception_handlers(),
)
oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="token")
password_hash = PasswordHash.recommended()


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # TODO actually fetch user and verify token
    ttoken = await Token.get(token=token)
    username = ttoken.username
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return User_Pydantic(username=username)


@app.post("/token", response_model=Token_Pydantic)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response):
    # TODO Replace with actual Database use and password verification and return token
    user = await User.get_or_none(username=form_data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    if not password_hash.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    # Generate token
    token = secrets.token_hex(32)
    # TODO hash token with SHA256
    ttoken = await Token.create(username=user.username, token=token)
    await ttoken.save()

    return {"access_token": token, "token_type": "bearer"}


# Post management
@app.get("/post/{id}", response_model=Post_Pydantic, responses={404: {"model": str}})
async def get_post(id: UUID):
    item = await Post.get_or_none(id=id)
    if not item:
        return (status.HTTP_404_NOT_FOUND, "No post under this ID")
    return await Post_Pydantic.from_tortoise_orm(item)


@app.post("/post")
async def create_post(post: Post_Pydantic, token: Annotated[User, Depends(get_current_user)]) -> UUID:
    # TODO Use actual User data
    id = uuid4()
    tpost = await Post.create(id=id, **post.model_dump())
    await tpost.save()
    return id

