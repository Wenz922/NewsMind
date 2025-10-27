from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create the SQLAlchemy database instance
db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = 'users'
    pass


# Article model
class Article(db.Model):
    __tablename__ = 'articles'
    pass


# ChatHistory model
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    pass

