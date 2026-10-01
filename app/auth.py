from .dependencies import get_session
from pwdlib import PasswordHash
import secrets
from typing import Annotated
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select, Session
from .models.sqlmodel import User, Token

oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="token")
password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def generate_token() -> str:
    # TODO hash token with SHA256
    return secrets.token_hex(32)


def save_token_for_user(session: Session, username: str, token: str):
    session.add(Token(username=username, token=token))
    session.commit()


def get_token_data(session: Session, token: str) -> Token | None:
    statement = select(Token).where(Token.token == token)
    results = session.exec(statement)
    return results.one_or_none()


def get_user(session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    results = session.exec(statement)
    user = results.one_or_none()
    return user


def get_user_from_token(session: Session, token: str) -> User | None:
    if token_data := get_token_data(session, token):
        if not token_data.username:
            return None
        return get_user(session, token_data.username)


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    if user := get_user(session, username):
        if verify_password(password, user.password_hash):
            return user
        return None

    # Run verify_password anyway so the difference in timing isn't noticable to malicious actors
    verify_password(password, DUMMY_HASH)
    return None


def get_current_user(
        session: Annotated[Session, Depends(get_session)], 
        token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    # TODO actually fetch user and verify token
    user = get_user_from_token(session, token)
    if not user:
        raise credentials_exception

    return user
