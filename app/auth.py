import os
from pwdlib import PasswordHash
import secrets
from typing import Annotated
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from .models.tortoise import Token, User
from .models.pydantic import User_Pydantic

oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="token")
password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def generate_token() -> str:
    # TODO hash token with SHA256
    return secrets.token_hex(32)


async def save_token_for_user(username: str, token: str):
    await Token.create(username=username, token=token)


async def get_token_data(token: str) -> Token | None:
    return await Token.get_or_none(token=token)


async def get_user(username: str) -> User | None:
    return await User.get_or_none(username=username)


async def get_user_from_token(token: str) -> User | None:
    if token_data := await get_token_data(token):
        if not token_data.username:
            return None
        return await get_user(token_data.username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


async def authenticate_user(username: str, password: str) -> User_Pydantic | None:
    if user := await get_user(username):
        if verify_password(password, user.password_hash):
            return await User_Pydantic.from_tortoise_orm(user)
        return None

    # Run verify_password anyway so the difference in timing isn't noticable to malicious actors
    verify_password(password, DUMMY_HASH)
    return None


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User_Pydantic:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    # TODO actually fetch user and verify token
    user = await get_user_from_token(token)
    if not user:
        raise credentials_exception

    return User_Pydantic.from_tortoise_orm(user)
