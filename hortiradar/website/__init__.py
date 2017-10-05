from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .processing import get_nsfw_prob, mark_as_spam

app = Flask(__name__)
app.config.from_pyfile("settings.py")
app.config.from_pyfile("settings-secret.py")

db = SQLAlchemy(app)            # initialize Flask-SQLAlchemy
