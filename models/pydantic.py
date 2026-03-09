from pydantic import BaseModel
from typing import TYPE_CHECKING, Literal
from models.tortoise import User, Post
from tortoise.contrib.pydantic import pydantic_model_creator, PydanticModel

if TYPE_CHECKING:   # pragma: nocoverage
    class User_Pydantic(User, PydanticModel):   # type:ignore[misc]
        pass
    class Post_Pydantic(Post, PydanticModel):   # type:ignore[misc]
        pass
else:
    User_Pydantic = pydantic_model_creator(User)
    Post_Pydantic = pydantic_model_creator(Post)

class Token_Pydantic(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
