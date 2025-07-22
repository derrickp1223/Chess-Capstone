from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!'
    from .routes import main
    app.register_blueprint(main)
    from .sockets import register_sockets
    register_sockets(socketio)
    socketio.init_app(app)
    return app