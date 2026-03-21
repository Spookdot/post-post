from pydantic import BaseModel
from typing import TYPE_CHECKING, Literal
from models.tortoise import User, Post, Tag
from tortoise.contrib.pydantic import pydantic_model_creator, PydanticModel
from tortoise import Tortoise

if TYPE_CHECKING:   # pragma: nocoverage
    class Tag_Pydantic(Tag, PydanticModel):   # type:ignore[misc]
        pass
    class User_Pydantic(User, PydanticModel):   # type:ignore[misc]
        pass
    class Post_Pydantic(Post, PydanticModel):   # type:ignore[misc]
        pass
else:
    Tortoise.init_models(["models.tortoise"], "models")
    Tag_Pydantic = pydantic_model_creator(Tag)
    User_Pydantic = pydantic_model_creator(User)
    Post_Pydantic = pydantic_model_creator(Post)

class Token_Pydantic(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
