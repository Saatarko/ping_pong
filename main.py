from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict

app = FastAPI()

rooms = {}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return HTMLResponse(open("static/choose_game.html", encoding="utf-8").read())

initial_game_state = {
    'ball': {'x': 400, 'y': 300, 'radius': 10},
    'player1': {'x': 350, 'y': 10, 'width': 100, 'height': 20},
    'player2': {'x': 350, 'y': 570, 'width': 100, 'height': 20}
}

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await websocket.accept()
    print(f"Connected to room: {room}")

    if room not in rooms:
        rooms[room] = {'players': {'player1': False, 'player2': False}, 'websockets': [], 'player_info': {}, 'game_state': initial_game_state}

    rooms[room]['websockets'].append(websocket)

    try:
        # Send initial game state
        await websocket.send_text(json.dumps({
            'type': 'game_state',
            **rooms[room]['game_state']
        }))

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"Received message: {message}")

            if message['type'] == 'identify_player':
                if len(rooms[room]['player_info']) < 2:
                    player = f'player{len(rooms[room]["player_info"]) + 1}'
                    rooms[room]['player_info'][player] = websocket
                    await websocket.send_text(json.dumps({
                        'type': 'identify_player',
                        'player': player
                    }))

            elif message['type'] == 'player_status':
                player = message['player']
                is_ready = message['isReady']
                rooms[room]['players'][player] = is_ready
                await broadcast_message(room, {
                    'type': 'update_players',
                    'players': rooms[room]['players']
                })

            elif message['type'] == 'start_game':
                await broadcast_message(room, {'type': 'game_started'})
                print(f"Game started in room {room}")

            elif message['type'] == 'player_update':
                player = message['player']
                position = message['position']
                rooms[room]['game_state'][player] = position
                await broadcast_message(room, {
                    'type': 'game_state',
                    **rooms[room]['game_state']
                })

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        rooms[room]['websockets'].remove(websocket)
        if not rooms[room]['websockets']:
            del rooms[room]


async def broadcast_message(room: str, message: dict):
    if room in rooms:
        for websocket in rooms[room]['websockets']:
            await websocket.send_text(json.dumps(message))

async def broadcast_game_state(room: str):
    state = {
        'ball': {
            'x': 400,  # Примерные значения, замените на актуальные
            'y': 300,
            'radius': 10
        },
        'player1': {
            'x': 350,
            'y': 10,
            'width': 100,
            'height': 20
        },
        'player2': {
            'x': 350,
            'y': 570,
            'width': 100,
            'height': 20
        }
    }
    await broadcast_message(room, {'type': 'game_state', **state})

# Пример обновления состояния игры
async def update_game_state(room: str, state: dict):
    await broadcast_message(room, {'type': 'game_state', **state})

@app.get("/game.html")
async def get_game_html():
    return HTMLResponse(open('static/game.html', 'r').read())
