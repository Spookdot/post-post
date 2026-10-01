from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import Self, TYPE_CHECKING

from .link import PostTagLink

if TYPE_CHECKING:
    from .post import Post

class TagBase(SQLModel):
    name: str = Field(max_length=256, primary_key=True)

    @classmethod
    def from_str(cls, name: str) -> Self:
        return cls(name=name)

class TagCreate(SQLModel):
    pass

class Tag(TagBase, table=True):
    posts: list["Post"] = Relationship(
        back_populates="tags", 
        link_model=PostTagLink
    )

    @classmethod
    def fetch_optional(cls, session: Session, name: str) -> Self | None:
        return session.exec(select(cls).where(cls.name == name)).one_or_none()

def tags_from_strings(names: list[str]) -> list[Tag]:
    return list(map(Tag.from_str, names))
