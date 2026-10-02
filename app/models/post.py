from sqlmodel import SQLModel, Session, Field, Relationship, select
from typing import Self, TYPE_CHECKING
from uuid import UUID
import uuid

from .link import PostTagLink

if TYPE_CHECKING:
    from .tag import Tag
    from .user import User

class PostBase(SQLModel):
    title: str = Field(max_length=64)
    content: str

    def into_convert(self) -> "PostConvert":
        return PostConvert.model_validate(self)

class PostConvert(PostBase):
    def into_create(self, tags: list[str]) -> "PostCreate":
        create = PostCreate(**self.model_dump())
        create.tags = tags
        return create

    def into_public(self, id: UUID, username: str, tags: list[str]) -> "PostPublic":
        public = PostPublic(**self.model_dump())
        public.id = id
        public.username = username
        public.tags = tags
        return public

    def into_table(self, user: "User") -> Post:
        table = Post(user=user, **self.model_dump())
        table.tags = []
        return table

class PostCreate(PostBase):
    tags: list[str] = Field(default=[])

class PostPublic(PostBase):
    id: UUID
    username: str
    tags: list[str] = Field(default=[])

    @classmethod
    def from_table(cls, post_table: "Post") -> Self:
        post_dict = post_table.model_dump()

        post_dict["tags"] = post_table.get_tags_as_str()

        return cls.model_validate(post_dict)

class Post(PostBase, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    username: str = Field(foreign_key="user.username")
    user: "User" = Relationship(back_populates="posts")
    tags: list["Tag"] = Relationship(
        back_populates="posts", 
        link_model=PostTagLink
    )

    def get_tags_as_str(self) -> list[str]:
        return list(map(lambda tag: tag.name, self.tags))

    def add_tags(self, tags: list["Tag"]):
        self.tags.extend(tags)

    @classmethod
    def fetch_optional(cls, session: Session, id: uuid.UUID) -> Self | None:
        return session.exec(select(cls).where(cls.id == id)).one_or_none()

    def into_public(self) -> PostPublic:
        return PostPublic.from_table(self)
