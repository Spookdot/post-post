from typing import Literal, Self
import uuid
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Engine

class PostTagLink(SQLModel, table=True):
    post_id: uuid.UUID | None = Field(default=None, foreign_key="post.id", primary_key=True)
    tag_name: str | None = Field(default=None, foreign_key="tag.name", primary_key=True)


class TagBase(SQLModel):
    name: str = Field(max_length=256, primary_key=True)

class TagCreate(SQLModel):
    pass

class Tag(TagBase, table=True):
    posts: list["Post"] = Relationship(back_populates="tags", link_model=PostTagLink)


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

    tags: list["Tag"] = Relationship(back_populates="posts", link_model=PostTagLink)

    def get_tags_as_str(self) -> list[str]:
        return list(map(lambda tag: tag.name, self.tags))

    @classmethod
    def from_create(cls, create: PostCreate) -> Self:
        # TODO implement
        base = PostBase.from_create(create)
        table = cls.model_validate(base)
        return table

    def into_public(self) -> PostPublic:
        return PostPublic.from_table(self)

class User(SQLModel, table=True):
    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=64)
    password_hash: str = Field(max_length=256)

class Token(SQLModel, table=True):
    username: str = Field(max_length=64, foreign_key="user.username")
    token: str = Field(max_length=64, primary_key=True)

class TokenResponse(SQLModel):
    access_token: str
    token_type: Literal["bearer"]

def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
