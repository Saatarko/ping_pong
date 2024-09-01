from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict
app = FastAPI()

rooms = {}

app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище для состояния игроков и игр
games: Dict[str, Dict[int, WebSocket]] = {}
game_states: Dict[str, Dict] = {}


@app.get("/")
async def get():
    return HTMLResponse(open("static/choose_game.html", encoding="utf-8").read())

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await websocket.accept()
    print(f"Connected to room: {room}")

    if room not in rooms:
        rooms[room] = {'players': {'player1': False, 'player2': False}, 'websockets': []}

    rooms[room]['websockets'].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"Received message: {message}")

            if message['type'] == 'player_status':
                player = message['player']
                is_ready = message['isReady']
                rooms[room]['players'][player] = is_ready
                await broadcast_message(room, {
                    'type': 'update_players',
                    'players': rooms[room]['players']
                })

            elif message['type'] == 'start_game':
                # Notify all clients that the game has started
                await broadcast_message(room, {'type': 'game_started'})
                # Optionally send initial game state here
                print(f"Game started in room {room}")

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

# Serve the game.html file
@app.get("/game.html")
async def get_game_html():
    with open('static/game.html', 'r') as file:
        return file.read()