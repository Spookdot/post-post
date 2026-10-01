from sqlalchemy import Engine
from sqlmodel import StaticPool
from fastapi import Depends
from typing import Annotated
from pydantic_settings import SettingsConfigDict
from pydantic import BaseModel
from functools import lru_cache
import sqlmodel

class Settings(BaseModel):
    test_user_username: str = "test"
    test_user_password: str = "test1234"
    db_url: str = "sqlite://"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()

@lru_cache()
def get_engine():
    settings = get_settings()
    return sqlmodel.create_engine(settings.db_url, poolclass=StaticPool)

def get_session(engine: Annotated[Engine, Depends(get_engine)]):
    with sqlmodel.Session(engine) as session:
        yield session
