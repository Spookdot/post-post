from sqlmodel import SQLModel, Session, Field, Relationship, select
from typing import Self, TYPE_CHECKING
import uuid

from .link import PostTagLink

if TYPE_CHECKING:
    from .tag import Tag

class PostBase(SQLModel):
    title: str = Field(max_length=64)
    content: str

    @classmethod
    def from_create(cls, create: "PostCreate") -> Self:
        return cls(**create.model_dump())

class PostCreate(PostBase):
    tags: list[str] = Field(default=[])

    def into_base(self) -> PostBase:
        return PostBase.from_create(self)

class PostPublic(PostBase):
    id: uuid.UUID
    tags: list[str] = Field(default=[])

    @classmethod
    def from_table(cls, post_table: "Post") -> Self:
        post_dict = post_table.model_dump()

        post_dict["tags"] = post_table.get_tags_as_str()

        return cls.model_validate(post_dict)

class Post(PostBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

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

    @classmethod
    def from_create(cls, create: PostCreate) -> Self:
        base = PostBase.from_create(create)
        table = cls.model_validate(base)
        return table

    def into_public(self) -> PostPublic:
        return PostPublic.from_table(self)
