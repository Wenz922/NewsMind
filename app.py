from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Article, UserArticle, ChatHistory, Statistics
from modules import news_fetcher, summarizer

import os
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


# -- Route Map ---
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter(User.username==username or User.email==email).first():
            flash("Username or email already exists.")
            return redirect("/register")

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        flash("Registration successfully, please login.")
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(username=request.form.get['username']).first()
    if user and user.check_password(request.form.get['password']):
        session['user_id'] = user.id
        user.last_login = datetime.utcnow()
        db.session.commit()
        return redirect('/digest')
    else:
        flash("Invalid username or password")
        return redirect("/")


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.")
    return redirect("/")


@app.route("/digest")
def digest():
    summaries = summarizer.summarize_article()
    return render_template("digest.html", summaries=summaries)


@app.route("/chat", methods=["GET", "POST"])
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
