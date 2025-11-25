from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Article, UserArticle, ChatHistory, Statistics
from modules import news_fetcher, summarizer, embedding_manager

import os
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime

# -- Flask Setup --
load_dotenv()

# Create the App
app = Flask(__name__)
# Configurate SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'data/newsmind.sqlite')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

db.init_app(app)  # Link the database and the app.


# --- Helper Decorator ---
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.")
            return redirect("/")
        return func(*args, **kwargs)
    return wrapper


# --- Route Map ---
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        language = request.form.get("language", "en")

        # correct duplicate check
        if User.query.filter(User.username==username or User.email==email).first():
            flash("Username or email already exists.")
            return redirect("/register")

        new_user = User(
            username=username,
            email=email,
            preferred_language=language
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successfully, please login.")
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(username=request.form['username']).first()
    if user and user.check_password(request.form['password']):
        session['user_id'] = user.id
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Redirect to select page, if user has no selected topics
        if not user.interests:
            return redirect("/select_topics")
        return redirect('/digest')
    else:
        flash("Invalid username or password")
        return redirect("/")


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.")
    return redirect("/")


@app.route("/select_topics", methods=["GET", "POST"])
@login_required
def select_topics():
    common_topics = [
        "technology", "science", "business", "health", "sports",
        "politics", "world", "entertainment", "lifestyle"
    ]

    if request.method == "POST":
        selected = request.form.getlist("topics")
        if not selected:
            flash("Please choose at least one topic.")
            return redirect("/select_topics")

        user = User.query.get(session["user_id"])
        user.interests = ", ".join(selected)
        db.session.commit()

        flash("Topics saved successfully!")
        return redirect("/refresh")

    return render_template("select_topics.html", topics=common_topics)


@app.route("/refresh")
@login_required
def refresh():
    user = User.query.get(session["user_id"])
    try:
        print(f"[NewsMind] Fetching personalized news for {user.username}...")

        topics = [t.strip() for t in user.interests.split(",") if t.strip()]
        total = 0
        for topic in topics:
            total += news_fetcher.fetch_from_newsapi(topic=topic, language=user.preferred_language)

        flash(f"Fetched {total}: {user.preferred_language.upper()} news for {user.username}.")
    except Exception as e:
        flash(f"Error during refresh: {e}")
        print("[NewsMind] Refresh error:", e)

    return redirect("/digest")


@app.route("/digest")
@login_required
def digest():
    user = User.query.get(session["user_id"])
    topics = [t.strip() for t in user.interests.split(",") if t.strip()]

    articles = (
        Article.query.filter(Article.category.in_(topics))
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )

    return render_template("digest.html", articles=articles)


@app.route("/article/<int:article_id>")
@login_required
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)

    # extract full text dynamically
    full_text = news_fetcher.extract_full_text(article.url)

    return render_template("article.html", article=article, full_text=full_text)


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        user_input = request.form.get("user_input")
        # todo: Connect chat_agent here
    return render_template("chat.html")


# --- Run App ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
