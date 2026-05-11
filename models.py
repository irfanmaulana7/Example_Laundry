from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    layanan = db.Column(db.String(100))
    berat = db.Column(db.Float)
    total = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Diterima")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    layanan = db.Column(db.String(100))
    berat = db.Column(db.Float)
    total = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Diterima")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 🔥 PENTING