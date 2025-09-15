import chess
from flask_socketio import emit, join_room
from flask import session
from . import socketio
from .models import db, Game

# In-memory board objects for active games
active_boards = {}

def register_sockets(socketio):

    @socketio.on('join')
    def handle_join(data):
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'You must be logged in to join a game.'})
            return

        room = data['room']
        join_room(room)

        # Load or create board
        game = Game.query.get(room)
        if not game:
            emit('error', {'message': 'Game not found.'})
            return

        # Initialize in-memory board if not present
        if room not in active_boards:
            board = chess.Board()
            # replay moves from DB
            for move_uci in game.moves.split():
                board.push_uci(move_uci)
            active_boards[room] = board

        emit('board_state', active_boards[room].fen(), to=room)

    @socketio.on('move')
    def handle_move(data):
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'You must be logged in to make a move.'})
            return

        room = data['room']
        move = data['move']

        game = Game.query.get(room)
        if not game:
            emit('error', {'message': 'Game not found.'})
            return

        # Ensure correct player is moving
        moves_list = game.moves.split() if game.moves else []
        is_white_turn = len(moves_list) % 2 == 0
        if (is_white_turn and game.player_white_id != user_id) or \
           (not is_white_turn and game.player_black_id != user_id):
            emit('error', {'message': 'Not your turn!'})
            return

        board = active_boards.get(room)
        if not board:
            board = chess.Board()
            for m in moves_list:
                board.push_uci(m)
            active_boards[room] = board

        try:
            board.push_uci(move)
            # Update DB
            moves_list.append(move)
            game.moves = ' '.join(moves_list)
            db.session.commit()

            emit('board_state', board.fen(), to=room)
        except:
            emit('invalid_move', {}, to=request.sid)
