from .link import *  # noqa: F403
from .post import *  # noqa: F403
from .tag import *  # noqa: F403
from .token import *  # noqa: F403
from .user import *  # noqa: F403

from sqlmodel import SQLModel
from sqlalchemy import Engine

class Message(SQLModel):
    message: str

def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
