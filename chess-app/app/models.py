from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'  # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    white_games = db.relationship('Game', foreign_keys='Game.player_white_id', backref='white_player')
    black_games = db.relationship('Game', foreign_keys='Game.player_black_id', backref='black_player')

    def __repr__(self):
        return f'<User {self.username}>'
    
class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    player_white_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player_black_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null for waiting games
    moves = db.Column(db.Text, nullable=True, default='')  # Store moves in UCI format
    status = db.Column(db.String(20), nullable=False, default='waiting')  # waiting, active, finished
    result = db.Column(db.String(10), nullable=True)  # 1-0, 0-1, 1/2-1/2, *
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Game {self.id} | White: {self.player_white_id} Black: {self.player_black_id} Status: {self.status}>"
    
    def get_moves_list(self):
        """Return moves as a list"""
        return self.moves.split() if self.moves else []
    
    def add_move(self, move_uci):
        """Add a move to the game"""
        moves_list = self.get_moves_list()
        moves_list.append(move_uci)
        self.moves = ' '.join(moves_list)
        self.updated_at = datetime.utcnow()

# Waiting queue for matchmaking
class WaitingQueue(db.Model):
    __tablename__ = 'waiting_queue'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='queue_entries')
    
    def __repr__(self):
        return f"<WaitingQueue user_id: {self.user_id}>"