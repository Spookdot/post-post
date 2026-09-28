from functools import lru_cache
from pydantic_settings import SettingsConfigDict
from pydantic import BaseModel
from typing import TYPE_CHECKING, Literal
from app.models.tortoise import User, Post, Tag
from tortoise.contrib.pydantic import pydantic_model_creator, PydanticModel
from tortoise import Tortoise

if TYPE_CHECKING:   # pragma: nocoverage
    class Tag_Pydantic(Tag, PydanticModel):   # type:ignore[misc]  # ty:ignore[invalid-method-override, conflicting-metaclass]
        pass
    class User_Pydantic(User, PydanticModel):   # type:ignore[misc]  # ty:ignore[invalid-method-override, conflicting-metaclass]
        pass
    class Post_Pydantic(Post, PydanticModel):   # type:ignore[misc]  # ty:ignore[invalid-method-override, conflicting-metaclass]
        pass
else:
    Tortoise.init_models(["app.models.tortoise"], "models")
    Tag_Pydantic = pydantic_model_creator(Tag)
    User_Pydantic = pydantic_model_creator(User)
    Post_Pydantic = pydantic_model_creator(Post, optional=["tags"])

class Token_Pydantic(BaseModel):
    access_token: str
    token_type: Literal["bearer"]

class Settings(BaseModel):
    test_user_username: str = "test"
    test_user_password: str = "test1234"
    db_url: str = "sqlite://:memory:"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
