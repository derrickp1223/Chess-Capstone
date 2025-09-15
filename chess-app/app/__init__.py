from flask import Flask
from flask_socketio import SocketIO
from .models import db

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)

    # Secret key
    app.config['SECRET_KEY'] = 'secret!'

    # PostgreSQL connection
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chess_user:Amber1984.@localhost/chess_capstone'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    with app.app_context():
        db.create_all()  # Create tables if they don’t exist

    # Register routes
    from .routes import main
    app.register_blueprint(main)

    # Initialize SocketIO
    socketio.init_app(app)

    # Register SocketIO events
    from .sockets import register_sockets
    register_sockets(socketio)

    return app