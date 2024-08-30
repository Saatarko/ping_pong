import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище для состояния игроков и игр
games: Dict[str, Dict[int, WebSocket]] = {}  # ключ игры -> {player_id -> websocket}
game_states: Dict[str, Dict] = {}  # ключ игры -> {game_running: bool, player_ids: set}

@app.get("/")
async def get():
    return HTMLResponse(open("static/game.html", encoding="utf-8").read())

@app.get("/games")
async def list_games():
    return {"games": list(games.keys())}

@app.post("/create_game")
async def create_game():
    game_key = f"game_{len(games)}"
    games[game_key] = {}
    game_states[game_key] = {'game_running': False, 'player_ids': set()}
    return {"game_key": game_key}

@app.websocket("/ws/{game_key}")
async def websocket_endpoint(websocket: WebSocket, game_key: str):
    if game_key not in games:
        await websocket.close()
        return

    await websocket.accept()

    if len(games[game_key]) == 0:
        # Первый игрок
        player_id = 1
    else:
        # Следующий игрок
        player_id = 2

    games[game_key][player_id] = websocket
    game_states[game_key]['player_ids'].add(player_id)

    # Уведомляем игрока о его идентификаторе
    await websocket.send_text(json.dumps({'type': 'playerId', 'playerId': player_id}))
    print(f"Assigned player ID {player_id} to connection")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message['type'] == 'player_update':
                # Отправляем обновление состояния игрока всем игрокам
                for pid, ws in games[game_key].items():
                    if ws != websocket:
                        await ws.send_text(json.dumps(message))

            elif message['type'] == 'game_state':
                # Отправляем обновленное состояние игры всем игрокам
                for pid, ws in games[game_key].items():
                    await ws.send_text(json.dumps(message))

            elif message['type'] == 'start_game':
                if len(game_states[game_key]['player_ids']) == 2:
                    # Уведомляем всех игроков, что игра началась
                    print(f"Received start_game command for game {game_key}")
                    game_states[game_key]['game_running'] = True
                    for pid, ws in games[game_key].items():
                        await ws.send_text(json.dumps({'type': 'game_started'}))
                else:
                    await websocket.send_text(json.dumps({'type': 'error', 'message': 'Not all players are connected.'}))

    except WebSocketDisconnect:
        # Удаляем соединение после отключения
        for pid, ws in games[game_key].items():
            if ws == websocket:
                del games[game_key][pid]
                game_states[game_key]['player_ids'].remove(pid)
                break

        if not games[game_key]:
            del games[game_key]
            del game_states[game_key]
    except Exception as e:
        print(f"Error: {e}")
