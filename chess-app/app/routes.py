from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, Game, WaitingQueue
from functools import wraps

main = Blueprint('main', __name__)

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# HOMEPAGE
@main.route('/')
def index():
    # Check if user is logged in
    user_id = session.get('user_id')
    user = None
    if user_id:
        user = User.query.get(user_id)
    return render_template('index.html', user=user)

# GAME PAGE
@main.route('/game/<int:game_id>')
@login_required
def game(game_id):
    user_id = session.get('user_id')
    game = Game.query.get_or_404(game_id)
    
    # Check if user is part of this game
    if user_id not in [game.player_white_id, game.player_black_id]:
        return jsonify({'error': 'Access denied'}), 403
    
    return render_template('game.html', game=game, user_id=user_id)

# SIGNUP
@main.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validation
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Check if user already exists
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Username or email already exists'}), 400
    
    try:
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after signup
        session['user_id'] = new_user.id
        return jsonify({
            'message': 'User created successfully',
            'user': {'id': new_user.id, 'username': new_user.username}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user'}), 500

# LOGIN
@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({
            'message': 'Login successful',
            'user': {'id': user.id, 'username': user.username}
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401
    
# LOGOUT
@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

# JOIN MATCHMAKING QUEUE
@main.route('/find-game', methods=['POST'])
@login_required
def find_game():
    user_id = session.get('user_id')
    
    # Check if user is already in queue
    existing_queue = WaitingQueue.query.filter_by(user_id=user_id).first()
    if existing_queue:
        return jsonify({'error': 'Already in queue'}), 400
    
    # Check if there's someone waiting
    waiting_player = WaitingQueue.query.filter(WaitingQueue.user_id != user_id).first()
    
    if waiting_player:
        # Create game with waiting player
        game = Game(
            player_white_id=waiting_player.user_id,
            player_black_id=user_id,
            status='active'
        )
        db.session.add(game)
        
        # Remove from queue
        db.session.delete(waiting_player)
        db.session.commit()
        
        return jsonify({
            'message': 'Game found!',
            'game_id': game.id,
            'color': 'black'
        }), 200
    else:
        # Add to queue
        queue_entry = WaitingQueue(user_id=user_id)
        db.session.add(queue_entry)
        db.session.commit()
        
        return jsonify({'message': 'Added to queue, waiting for opponent...'}), 200

# GET CURRENT USER INFO
@main.route('/user', methods=['GET'])
@login_required
def get_user():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    })

# GET USER'S GAMES
@main.route('/my-games', methods=['GET'])
@login_required
def my_games():
    user_id = session.get('user_id')
    games = Game.query.filter(
        (Game.player_white_id == user_id) | (Game.player_black_id == user_id)
    ).order_by(Game.updated_at.desc()).all()
    
    games_data = []
    for game in games:
        games_data.append({
            'id': game.id,
            'status': game.status,
            'result': game.result,
            'created_at': game.created_at.isoformat(),
            'updated_at': game.updated_at.isoformat(),
            'my_color': 'white' if game.player_white_id == user_id else 'black',
            'opponent': game.black_player.username if game.player_white_id == user_id else game.white_player.username
        })
    
    return jsonify({'games': games_data})