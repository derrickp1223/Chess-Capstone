from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'
    
class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    player_white_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player_black_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    moves = db.Column(db.Text, nullable=True)  # Store moves in PGN format
    status = db.Column(db.String(20), nullable=False, default='waiting')  # waiting, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Game {self.id} | White: {self.player_white_id} Black: {self.player_black_id}>"