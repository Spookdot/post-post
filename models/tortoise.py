from tortoise import Model, fields

class Post(Model):
    id = fields.UUIDField(primary_key=True)
    title = fields.CharField(max_length=64)
    content = fields.TextField()

class User(Model):
    id = fields.UUIDField(primary_key=True)
    username = fields.CharField(max_length=64)
    password_hash = fields.CharField(max_length=256)

class Token(Model):
    username = fields.CharField(max_length=64)
    token = fields.CharField(max_length=64)
