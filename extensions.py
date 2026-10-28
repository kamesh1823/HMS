"""
extensions.py
Holds Flask extensions so they can be imported anywhere without circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
