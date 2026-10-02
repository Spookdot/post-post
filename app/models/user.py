from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .post import Post

class User(SQLModel, table=True):
    username: str = Field(max_length=64, primary_key=True)
    password_hash: str = Field(max_length=256)

    posts: list["Post"] = Relationship(back_populates="user")

    @classmethod
    def fetch_optional(cls, session: Session, username: str) -> User | None:
        return session.exec(select(cls).where(cls.username == username)).one_or_none()
