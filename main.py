from tortoise.contrib.fastapi import RegisterTortoise, tortoise_exception_handlers
from tortoise.config import DBUrlConfig, AppConfig
from tortoise import TortoiseConfig
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from uuid import UUID, uuid4
import secrets

from models.tortoise import Post as TPost, User as TUser, Token as TToken
from models.pydantic import Post, User

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    tortoise_config = TortoiseConfig(
        connections={"default": DBUrlConfig("sqlite://:memory:")},
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
        test_user = await TUser.create(username="springjordan", password_hash="$argon2id$v=19$m=65536,t=3,p=4$A7mxd1AfqpkZLdue4VOHWg$mclJnQ3BIZkEvADQTfwdpQSSSuS9hoGa7Ik+groHkPY")
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
    ttoken = await TToken.get(token=token)
    username = ttoken.username
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return User(username=username)


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response):
    # TODO Replace with actual Database use and password verification and return token
    tuser = await TUser.get_or_none(username=form_data.username)
    if not tuser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    if not password_hash.verify(form_data.password, tuser.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    # Generate token
    token = secrets.token_hex(32)
    # TODO hash token with SHA256
    ttoken = await TToken.create(username=tuser.username, token=token)
    await ttoken.save()

    return {"access_token": token, "token_type": "bearer"}


# Post management
@app.get("/post/{id}")
async def get_post(id: UUID) -> Post | None:
    item = await TPost.get_or_none(id=id)
    return Post.model_validate(item)


@app.post("/post")
async def create_post(post: Post, token: Annotated[User, Depends(get_current_user)]) -> UUID:
    # TODO Use actual User data
    id = uuid4()
    tpost = await TPost.create(id=id, **post.model_dump())
    await tpost.save()
    return id

