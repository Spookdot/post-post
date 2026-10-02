from sqlmodel import SQLModel, Field, Session, select
from typing import Literal, Self

class Token(SQLModel, table=True):
    username: str = Field(max_length=64, foreign_key="user.username")
    token: str = Field(max_length=64, primary_key=True)

    @classmethod
    def fetch_optional(cls, session: Session, token: str) -> Self | None:
        return session.exec(select(cls).where(cls.token == token)).one_or_none()

class TokenResponse(SQLModel):
    access_token: str
    token_type: Literal["bearer"]
