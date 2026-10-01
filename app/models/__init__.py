from .link import *
from .post import *
from .tag import *
from .token import *
from .user import *

from sqlmodel import SQLModel
from sqlalchemy import Engine

def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
