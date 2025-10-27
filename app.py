from flask import Flask, render_template, request
from models import db, User, Article, ChatHistory
from dotenv import load_dotenv

import os

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


# -- Route Map
@app.route("/")
def index():
    return "Hello World!"





# --- Run App ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
