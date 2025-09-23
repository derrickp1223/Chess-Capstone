import chess
from flask_socketio import emit, join_room, leave_room
from flask import session, request
from .models import db, Game, User, WaitingQueue

# In-memory board objects for active games
active_boards = {}
# Track connected users per room
room_users = {}
# Track users in matchmaking queue (socket_id -> user_id)
queue_sockets = {}

def register_sockets(socketio):

    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid}")
        
        # Remove from matchmaking queue if they were waiting
        if request.sid in queue_sockets:
            user_id = queue_sockets[request.sid]
            # Remove from database queue
            queue_entry = WaitingQueue.query.filter_by(user_id=user_id).first()
            if queue_entry:
                db.session.delete(queue_entry)
                db.session.commit()
            del queue_sockets[request.sid]
        
        # Clean up room_users if needed
        for room_id in list(room_users.keys()):
            if request.sid in room_users[room_id]:
                room_users[room_id].discard(request.sid)
                if not room_users[room_id]:
                    del room_users[room_id]

    @socketio.on('join_matchmaking')
    def handle_join_matchmaking(data=None):
        """Handle joining the matchmaking queue via WebSocket"""
        # Get user_id from the data passed from frontend
        user_id = data.get('user_id') if data else session.get('user_id')
        if not user_id:
            emit('error', {'message': 'You must be logged in to join matchmaking.'})
            return

        # Check if user is already in queue
        existing_queue = WaitingQueue.query.filter_by(user_id=user_id).first()
        if existing_queue:
            emit('matchmaking_status', {'status': 'already_in_queue'})
            return

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
            
            # Remove both players from queue
            db.session.delete(waiting_player)
            db.session.commit()
            
            # Remove waiting player from socket queue tracking
            waiting_socket_id = None
            for socket_id, queued_user_id in queue_sockets.items():
                if queued_user_id == waiting_player.user_id:
                    waiting_socket_id = socket_id
                    break
            
            if waiting_socket_id:
                del queue_sockets[waiting_socket_id]
                # Notify waiting player
                emit('game_found', {
                    'game_id': game.id,
                    'color': 'white',
                    'opponent': User.query.get(user_id).username
                }, to=waiting_socket_id)
            
            # Notify current player
            emit('game_found', {
                'game_id': game.id,
                'color': 'black',
                'opponent': User.query.get(waiting_player.user_id).username
            })
            
        else:
            # Add to queue
            queue_entry = WaitingQueue(user_id=user_id)
            db.session.add(queue_entry)
            db.session.commit()
            
            # Track socket for this user
            queue_sockets[request.sid] = user_id
            
            emit('matchmaking_status', {'status': 'waiting'})

    @socketio.on('leave_matchmaking')
    def handle_leave_matchmaking(data=None):
        """Handle leaving the matchmaking queue"""
        user_id = data.get('user_id') if data else session.get('user_id')
        if not user_id:
            return

        # Remove from database queue
        queue_entry = WaitingQueue.query.filter_by(user_id=user_id).first()
        if queue_entry:
            db.session.delete(queue_entry)
            db.session.commit()

        # Remove from socket tracking
        if request.sid in queue_sockets:
            del queue_sockets[request.sid]

        emit('matchmaking_status', {'status': 'left_queue'})

    @socketio.on('join_game')
    def handle_join_game(data):
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'You must be logged in to join a game.'})
            return

        game_id = data.get('game_id')
        if not game_id:
            emit('error', {'message': 'Game ID required.'})
            return

        # Load game from database
        game = Game.query.get(game_id)
        if not game:
            emit('error', {'message': 'Game not found.'})
            return

        # Check if user is part of this game
        if user_id not in [game.player_white_id, game.player_black_id]:
            emit('error', {'message': 'Access denied to this game.'})
            return

        room = f"game_{game_id}"
        join_room(room)

        # Track users in room
        if room not in room_users:
            room_users[room] = set()
        room_users[room].add(request.sid)

        # Initialize board if not present
        if room not in active_boards:
            board = chess.Board()
            # Replay moves from database
            moves_list = game.get_moves_list()
            try:
                for move_uci in moves_list:
                    if move_uci:  # Ensure move is not empty
                        board.push_uci(move_uci)
                active_boards[room] = board
            except ValueError as e:
                print(f"Error replaying moves for game {game_id}: {e}")
                # Reset to starting position if moves are corrupted
                active_boards[room] = chess.Board()

        board = active_boards[room]
        
        # Determine user's color
        user_color = 'white' if game.player_white_id == user_id else 'black'
        
        # Send game state to the joining user
        emit('game_joined', {
            'game_id': game_id,
            'fen': board.fen(),
            'color': user_color,
            'turn': 'white' if board.turn else 'black',
            'status': game.status,
            'moves': game.get_moves_list(),
            'white_player': game.white_player.username,
            'black_player': game.black_player.username if game.black_player else 'Waiting...'
        })

        # Notify other players in the room
        emit('player_joined', {
            'username': User.query.get(user_id).username,
            'color': user_color
        }, to=room, include_self=False)

        print(f"User {user_id} joined game {game_id}")

    @socketio.on('make_move')
    def handle_make_move(data):
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'You must be logged in to make a move.'})
            return

        game_id = data.get('game_id')
        move_uci = data.get('move')
        
        if not game_id or not move_uci:
            emit('error', {'message': 'Game ID and move required.'})
            return

        game = Game.query.get(game_id)
        if not game:
            emit('error', {'message': 'Game not found.'})
            return

        if game.status != 'active':
            emit('error', {'message': 'Game is not active.'})
            return

        # Check if it's the player's turn
        moves_list = game.get_moves_list()
        is_white_turn = len(moves_list) % 2 == 0
        
        if (is_white_turn and game.player_white_id != user_id) or \
           (not is_white_turn and game.player_black_id != user_id):
            emit('error', {'message': 'Not your turn!'})
            return

        room = f"game_{game_id}"
        board = active_boards.get(room)
        
        if not board:
            # Reconstruct board if not in memory
            board = chess.Board()
            for move in moves_list:
                if move:
                    try:
                        board.push_uci(move)
                    except ValueError:
                        emit('error', {'message': 'Game state corrupted.'})
                        return
            active_boards[room] = board

        try:
            # Validate and make the move
            chess_move = chess.Move.from_uci(move_uci)
            if chess_move in board.legal_moves:
                board.push(chess_move)
                
                # Update database
                game.add_move(move_uci)
                
                # Check for game end conditions
                if board.is_checkmate():
                    game.status = 'finished'
                    game.result = '1-0' if not board.turn else '0-1'  # Opposite of current turn wins
                elif board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                    game.status = 'finished'
                    game.result = '1/2-1/2'
                
                db.session.commit()

                # Broadcast move to all players in the room
                emit('move_made', {
                    'move': move_uci,
                    'fen': board.fen(),
                    'turn': 'white' if board.turn else 'black',
                    'status': game.status,
                    'result': game.result,
                    'check': board.is_check(),
                    'legal_moves': [move.uci() for move in board.legal_moves]
                }, to=room)

                print(f"Move made in game {game_id}: {move_uci}")
                
            else:
                emit('error', {'message': 'Illegal move.'})
        
        except ValueError as e:
            emit('error', {'message': f'Invalid move format: {str(e)}'})
        except Exception as e:
            print(f"Error handling move: {e}")
            emit('error', {'message': 'Error processing move.'})

    @socketio.on('leave_game')
    def handle_leave_game(data):
        game_id = data.get('game_id')
        if game_id:
            room = f"game_{game_id}"
            leave_room(room)
            
            # Clean up room tracking
            if room in room_users:
                room_users[room].discard(request.sid)
                if not room_users[room]:
                    # Last player left, clean up board
                    if room in active_boards:
                        del active_boards[room]
                    del room_users[room]
            
            print(f"User left game {game_id}")

    @socketio.on('get_legal_moves')
    def handle_get_legal_moves(data):
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Authentication required.'})
            return
        
        game_id = data.get('game_id')
        room = f"game_{game_id}"
        board = active_boards.get(room)
        
        if board:
            legal_moves = [move.uci() for move in board.legal_moves]
            emit('legal_moves', {'moves': legal_moves})
        else:
            emit('error', {'message': 'Game board not found.'})