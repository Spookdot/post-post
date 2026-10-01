from sqlmodel import SQLModel, Field
import uuid

class User(SQLModel, table=True):
    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=64)
    password_hash: str = Field(max_length=256)
