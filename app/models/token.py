from sqlmodel import SQLModel, Field
from typing import Literal

class Token(SQLModel, table=True):
    username: str = Field(max_length=64, foreign_key="user.username")
    token: str = Field(max_length=64, primary_key=True)

class TokenResponse(SQLModel):
    access_token: str
    token_type: Literal["bearer"]
