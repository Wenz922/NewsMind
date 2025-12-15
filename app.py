from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from models import db, User, Article, UserArticle, ChatHistory, Statistics
from modules import news_fetcher, summarizer, embedding_manager

import os
import json
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
# Helper function
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


def get_current_user():
    """Get the currently logged-in user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def get_or_create_user_article(user_id, article_id):
    """Get or create a UserArticle row for this user & article."""
    ua = UserArticle.query.filter_by(user_id=user_id, article_id=article_id).first()
    if ua is None:
        ua = UserArticle(
            user_id=user_id,
            article_id=article_id,
            action=json.dumps([]),  # JSON list of ["viewed", "liked", "linked"]
            timestamp=datetime.utcnow(),
        )
        db.session.add(ua)
        db.session.commit()
    return ua


def add_user_action(ua, action_name):
    """Append action_name to ua.action JSON list 'viewed', 'liked', or 'linked'."""
    try:
        actions = json.loads(ua.action) if ua.action else []
    except:
        actions = []

    if action_name not in actions:
        actions.append(action_name)

    ua.action = json.dumps(actions)
    ua.timestamp = datetime.utcnow()


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

        # Duplicate check
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
        flash("Registration successfully, please log in.")
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

    logging.warning(f"Failed login attempt for username '{username}'.")
    flash("Invalid username or password")
    return redirect("/")


@app.route("/logout")
@login_required
def logout():
    user = get_current_user()
    user_name = user.username if user else "unknown"
    session.pop('user_id', None)
    logging.info(f"User {user_name} logged out.")
    flash("Logged out successfully.")
    return redirect("/")


@app.route("/select_topics", methods=["GET", "POST"])
@login_required
def select_topics():
    common_topics = [
        "technology", "science", "business", "health", "sports",
        "politics", "world", "entertainment", "lifestyle"
    ]

    user = get_current_user()

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
    user = get_current_user()

    logging.info(f"User {user.username} triggered refresh (loading screen shown).")
    return render_template("refreshing.html")


@app.route("/refresh_process")
@login_required
def refresh_process():
    user = get_current_user()

    try:
        topics = [t.strip() for t in (user.interests or "").split(",") if t.strip()]
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

    return {"status": "done", "new_articles": total_new}


@app.route("/digest")
@login_required
def digest():
    user = get_current_user()
    topics = [t.strip() for t in (user.interests or "").split(",") if t.strip()]

    articles = (
        Article.query.filter(Article.category.in_(topics))
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )

    logging.info(f"User {user.username} visited digest page. Showing {len(articles)} articles.")
    return render_template("digest.html", articles=articles)


# Full Article View + Interactions (viewed, liked, linked), rating, notes
@app.route("/article/<int:article_id>")
@login_required
def article_detail(article_id):
    user = get_current_user()
    article = db.session.get(Article, article_id)
    if article is None:
        logging.warning(f"Article {article_id} not found.")
        abort(404)

    # Action "viewed"
    ua = get_or_create_user_article(user.id, article_id)
    add_user_action(ua, "viewed")
    db.session.commit()

    logging.info(f"User {user.username} viewed article {article_id}: {article.title}")

    # extract full text dynamically
    full_text = news_fetcher.extract_full_text(article.url)

    return render_template("article.html", article=article, full_text=full_text, ua=ua)


@app.route("/article/<int:article_id>/like", methods=["POST"])
@login_required
def like_article(article_id):
    user = get_current_user()
    article = db.session.get(Article, article_id)
    if article is None:
        logging.warning(f"Article {article_id} not found.")
        abort(404)

    # Action "liked"
    ua = get_or_create_user_article(user.id, article_id)
    add_user_action(ua, "liked")
    db.session.commit()

    logging.info(f"User {user.username} liked article {article_id}: {article.title}")

    return redirect(url_for("article_detail", article_id=article_id))


@app.route("/article/<int:article_id>/rate", methods=["POST"])
@login_required
def rate_article(article_id):
    user = get_current_user()
    article = db.session.get(Article, article_id)
    if article is None:
        logging.warning(f"Article {article_id} not found.")
        abort(404)

    ua = get_or_create_user_article(user.id, article_id)

    # Add rating
    try:
        rating = int(request.form.get("rating"))
        rating = max(1, min(10, rating))
    except:
        flash("Invalid rating.")
        return redirect(url_for("article_detail", article_id=article_id))

    ua.rating = rating
    ua.timestamp = datetime.utcnow()
    db.session.commit()

    logging.info(f"User {user.username} rated article {article_id} as {rating}/10.")

    return redirect(url_for("article_detail", article_id=article_id))


@app.route("/article/<int:article_id>/notes", methods=["POST"])
@login_required
def save_notes(article_id):
    user = get_current_user()
    article = db.session.get(Article, article_id)
    if article is None:
        logging.warning(f"Article {article_id} not found.")
        abort(404)

    ua = get_or_create_user_article(user.id, article_id)

    # Add notes
    notes = request.form.get("notes", "").strip()
    ua.notes = notes
    ua.timestamp = datetime.utcnow()
    db.session.commit()

    logging.info(f"User {user.username} added notes to article {article_id}.")

    return redirect(url_for("article_detail", article_id=article_id))


@app.route("/article/<int:article_id>/open_original")
@login_required
def open_original(article_id):
    user = get_current_user()
    article = db.session.get(Article, article_id)
    if article is None:
        logging.warning(f"Article {article_id} not found.")
        abort(404)

    ua = get_or_create_user_article(user.id, article_id)
    # Action "linked"
    add_user_action(ua, "linked")
    db.session.commit()

    logging.info(f"User {user.username} opened original link for {article_id}.")

    return redirect(article.url)


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
    logging.info("NewsMind Flask App started.")
    app.run(debug=True)
