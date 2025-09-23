import os
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Get port from environment variable (for deployment) or use 5000
    port = int(os.environ.get('PORT', 5002))
    
    # Get debug setting from environment
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Chess App on port {port}")
    print(f"Debug mode: {debug}")
    
    socketio.run(
        app, 
        debug=debug, 
        host='0.0.0.0',  # Allow external connections
        port=port,
        allow_unsafe_werkzeug=True  # For development with SocketIO
    )