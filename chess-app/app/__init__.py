from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from .models import db
import os

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Use environment variable for secret key or generate a random one
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # PostgreSQL connection - use environment variables for security
    database_url = os.environ.get('DATABASE_URL', 
                                'postgresql://chess_user:Nelson1984.@localhost:5433/chess_db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    with app.app_context():
        db.create_all()  # Create tables if they don't exist

    # Register routes
    from .routes import main
    app.register_blueprint(main)

    # Initialize SocketIO
    socketio.init_app(app)

    # Register SocketIO events
    from .sockets import register_sockets
    register_sockets(socketio)

    return app