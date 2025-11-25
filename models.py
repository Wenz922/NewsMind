from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create the SQLAlchemy database instance
db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)

    interests = db.Column(db.String(500))
    preferred_language = db.Column(db.String(50), nullable=False, default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Set password
    def set_password(self, password):
        # force Werkzeug to use pbkdf2 instead of scrypt
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    # verify password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Relationship to user_articles
    user_articles = db.relationship('UserArticle', backref='user', lazy=True, cascade="all, delete")
    # Relationship to chat_history
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"

    def __str__(self):
        return f"User: {self.username}"


# Article model
class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(100))
    source = db.Column(db.String(500))
    url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    published_at = db.Column(db.String(100))
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)  # LLM-generated summary
    embedding = db.Column(db.Text)  # JSON string for semantic search
    sentiment = db.Column(db.String(50))   # e.g., “positive”, “neutral”, “negative”

    # Relationship to articles
    user_articles = db.relationship('UserArticle', backref='article', lazy=True, cascade="all, delete")
    # Relationship to chat_history
    chat_history = db.relationship('ChatHistory', backref='article', lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<Article {self.id}: {self.title} by {self.author} at {self.published_at}>"

    def __str__(self):
        return f"Article: {self.title} by {self.author} at {self.published_at} from {self.source} describes: {self.summary}"


# UserArticle model
class UserArticle(db.Model):
    __tablename__ = 'user_articles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action = db.Column(db.String(30), nullable=False)  # e.g., “liked”, “viewed”, “shared”
    rating = db.Column(db.Integer)  # e.g., 1-10 score
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # The changed time when user does action

    # Link UserArticle to User with foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Link UserArticle to Article with foreign key
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)

    def __repr__(self):
        return f"<User Article {self.id}: {self.action}>"

    def __str__(self):
        return f"User Article: {self.action}, rating: {self.rating}, notes: {self.notes}"


# ChatHistory model
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role = db.Column(db.String(10), nullable=False)  # "user" or "bot"
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Link ChatHistory to User with foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Link ChatHistory to Article with foreign key
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True)

    def __repr__(self):
        return f"<Chat History {self.id}: {self.message} by {self.role}>"

    def __str__(self):
        return f"Chat History - {self.role}: {self.message}"


# Statistics model
class Statistics(db.Model):
    __tablename__ = 'statistics'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    topic = db.Column(db.String(100), nullable=False)
    sentiment_avg = db.Column(db.Float, nullable=False)
    mention_count = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Statistics {self.id}: {self.topic}>"

    def __str__(self):
        return f"Statistics: {self.topic} at {self.date} - mentioned: {self.mention_count}, avg. sentiment: {self.sentiment_avg}"
