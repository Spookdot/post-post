from sqlmodel import SQLModel, Session, Field, Relationship, select
from typing import Self, TYPE_CHECKING
from uuid import UUID
import uuid

from .link import PostTagLink

if TYPE_CHECKING:
    from .tag import Tag
    from .user import User

class PostBase(SQLModel):
    title: str | None = Field(max_length=64, default=None)
    content: str | None = Field(default=None)

    def into_convert(self) -> "PostConvert":
        return PostConvert.model_validate(self)

class PostConvert(PostBase):
    def into_create(self, tags: list[str]) -> "PostCreate":
        create = PostCreate(
            tags=tags,
            **self.model_dump()
        )
        return create

    def into_create_reblog(self, tags: list[str], reblog: UUID) -> "PostCreateReblog":
        create = PostCreateReblog(
            tags=tags,
            reblog=reblog,
            **self.model_dump()
        )
        return create

    def into_public(self, id: UUID, username: str, tags: list[str], reblog_of_id: UUID | None = None) -> "PostPublic":
        public = PostPublic(
            id=id, 
            username=username, 
            tags=tags, 
            reblog_of_id=reblog_of_id,
            **self.model_dump()
        )
        return public

    def into_table(self, user: "User") -> Post:
        table = Post(user=user, **self.model_dump())
        table.tags = []
        table.reblog_of_id = None
        return table

class PostCreate(PostBase):
    title: str
    content: str
    tags: list[str] = Field(default=[])
    reblog: None = Field(default=None)

class PostCreateReblog(PostBase):
    tags: list[str] = Field(default=[])
    reblog: UUID

class PostPublic(PostBase):
    id: UUID
    username: str
    tags: list[str] = Field(default=[])
    reblog_of_id: UUID | None = Field(default=None)

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

    reblog_of_id: UUID | None = Field(default=None, foreign_key="post.id")
    reblogs: list["Post"] = Relationship()

    def get_tags_as_str(self) -> list[str]:
        return list(map(lambda tag: tag.name, self.tags))

    def add_tags(self, tags: list["Tag"]):
        self.tags.extend(tags)

    @classmethod
    def fetch_optional(cls, session: Session, id: uuid.UUID) -> Self | None:
        return session.exec(select(cls).where(cls.id == id)).one_or_none()

    def into_public(self) -> PostPublic:
        return PostPublic.from_table(self)
