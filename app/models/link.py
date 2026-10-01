from sqlmodel import SQLModel, Field
import uuid

class PostTagLink(SQLModel, table=True):
    post_id: uuid.UUID | None = Field(default=None, foreign_key="post.id", primary_key=True)
    tag_name: str | None = Field(default=None, foreign_key="tag.name", primary_key=True)
