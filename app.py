from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Article, UserArticle, ChatHistory, Statistics
from modules import news_fetcher, summarizer, embedding_manager

import os
import logging
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime


# -------------------------------------------------------
# Flask Setup
# -------------------------------------------------------
load_dotenv()

# Create the App
app = Flask(__name__)
# Configurate SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'data/newsmind.sqlite')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

db.init_app(app)  # Link the database and the app.


# -------------------------------------------------------
# Logging Setup
# -------------------------------------------------------
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename="logs/newsmind.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# -------------------------------------------------------
# Login Required Decorator
# -------------------------------------------------------
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.")
            logging.warning("Unauthorized access attempt.")
            return redirect("/")
        return func(*args, **kwargs)
    return wrapper


# -------------------------------------------------------
# Route Map
# -------------------------------------------------------
@app.route("/")
def home():
    logging.info("Home page visited.")
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        language = request.form.get("language", "en")

        # Proper duplicate check
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.")
            logging.warning(f"Registration failed: Duplicate user '{username}' or email '{email}'.")
            return redirect("/register")

        new_user = User(
            username=username,
            email=email,
            preferred_language=language
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        logging.info(f"New user registered: {username}")
        flash("Registration successfully, please login.")
        return redirect("/")

    logging.info("Registration page visited.")
    return render_template("register.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        session['user_id'] = user.id
        user.last_login = datetime.utcnow()
        db.session.commit()

        logging.info(f"User logged in: {user.username}")

        # Redirect to select page, if user has no selected topics
        if not user.interests:
            return redirect("/select_topics")
        return redirect('/digest')
    else:
        logging.warning(f"Failed login attempt for username '{username}'.")
        flash("Invalid username or password")
        return redirect("/")


@app.route("/logout")
@login_required
def logout():
    user_id = session['user_id']
    session.pop('user_id', None)
    logging.info(f"User {user_id} logged out.")
    flash("Logged out successfully.")
    return redirect("/")


@app.route("/select_topics", methods=["GET", "POST"])
@login_required
def select_topics():
    common_topics = [
        "technology", "science", "business", "health", "sports",
        "politics", "world", "entertainment", "lifestyle"
    ]

    user = db.session.get(User, session["user_id"])

    if request.method == "POST":
        selected_topics = request.form.getlist("topics")

        if not selected_topics:
            flash("Please choose at least one topic.")
            logging.warning(f"User {user.username} attempted to save empty topics list.")
            return redirect("/select_topics")

        user.interests = ", ".join(selected_topics)
        db.session.commit()

        logging.info(f"User {user.username} selected topics: {selected_topics}")

        flash("Topics saved successfully!")
        return redirect("/refresh")

    logging.info(f"User {user.username} visited select_topics page.")
    return render_template("select_topics.html", topics=common_topics)


@app.route("/refresh")
@login_required
def refresh():
    user = User.query.get(session["user_id"])
    logging.info(f"User {user.username} triggered refresh (loading screen shown).")
    return render_template("refreshing.html")


@app.route("/refresh_process")
@login_required
def refresh_process():
    user = db.session.get(User, session["user_id"])
    try:
        topics = [t.strip() for t in user.interests.split(",") if t.strip()]
        logging.info(f"Starting news refresh for user {user.username}. Topics: {topics}")

        total_new = 0
        for topic in topics:
            added = news_fetcher.fetch_from_newsapi(topic=topic, language=user.preferred_language)
            logging.info(f"Topic '{topic}' added {added} new articles.")
            total_new += added

        logging.info(f"Completed refresh for user {user.username}. Total new articles: {total_new}")

        flash(f"Fetched {total_new}: {user.preferred_language.upper()} news for {user.username}.")
    except Exception as e:
        flash(f"Error during refresh: {e}")
        print("[NewsMind] Refresh error:", e)

    return {"status": "done"}


@app.route("/digest")
@login_required
def digest():
    user = db.session.get(User, session["user_id"])
    topics = [t.strip() for t in user.interests.split(",") if t.strip()]

    articles = (
        Article.query.filter(Article.category.in_(topics))
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )

    logging.info(f"User {user.username} visited digest page. Showing {len(articles)} articles.")
    return render_template("digest.html", articles=articles)


@app.route("/article/<int:article_id>")
@login_required
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    user = db.session.get(User, session["user_id"])

    logging.info(f"User {user.username} opened article ID {article_id} – {article.title}")

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
