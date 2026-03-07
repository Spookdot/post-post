from pydantic import BaseModel

class Post(BaseModel):
    title: str
    content: str

class User(BaseModel):
    username: str
