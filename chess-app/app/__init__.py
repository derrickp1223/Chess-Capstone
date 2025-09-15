from flask import Flask
from flask_socketio import SocketIO
from .models import db

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)

    # Secret key
    app.config['SECRET_KEY'] = 'secret!'
    
    # PostgreSQL 
    app.config['SQLALCHEMY_DATABSE_URI'] = 'postgresql://chess_user:Nelson1984.@localhost/chess_capstone'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    with app.app_context():
        db.create_all() # Create tables if there aren't any

    # Register routes
    from .routes import main
    app.register_blueprint(main)

    # Register SocetIO events
    from .sockets import register_sockets
    register_sockets(socketio)
    socketio.init_app(app)

    return app
