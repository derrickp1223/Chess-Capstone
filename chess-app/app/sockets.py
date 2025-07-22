import chess
from flask_socketio import emit, join_room
from . import socketio

games = {}

def register_sockets(socketio):
    @socketio.on('join')
    def handle_join(data):
        room = data['room']
        join_room(room)
        if room not in games:
            games[room] = chess.Board()
        emit('board_state', games[room].fen(), to=room)

    @socketio.on('move')
    def handle_move(data):
        room = data['room']
        move = data['move']
        board = games[room]
        try:
            board.push_uci(move)
            emit('board_state', board.fen(), to=room)
        except:
            emit('invalid_move', {}, to=request.sid)