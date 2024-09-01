import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
from starlette.websockets import WebSocketDisconnect, WebSocketState, WebSocket
import asyncio


app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")

# Constants
BALL_RADIUS = 10
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
BALL_SPEED = 5
canvas_width = 800
canvas_height = 600

initial_game_state = {
    'ball': {'x': 400, 'y': 300, 'dx': BALL_SPEED, 'dy': BALL_SPEED, 'radius': BALL_RADIUS},
    'player1': {'x': 350, 'y': 10, 'width': PADDLE_WIDTH, 'height': PADDLE_HEIGHT},
    'player2': {'x': 350, 'y': 570, 'width': PADDLE_WIDTH, 'height': PADDLE_HEIGHT},
    'scores': {'player1': 0, 'player2': 0}
}

rooms = {}

@app.get("/")
async def get():
    return HTMLResponse(open("static/choose_game.html", encoding="utf-8").read())


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await websocket.accept()
    print(f"Connected to room: {room}")

    if room not in rooms:
        rooms[room] = {
            'players': {'player1': False, 'player2': False},
            'websockets': [],
            'player_info': {},
            'game_state': initial_game_state.copy(),
            'game_started': False
        }

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
                if all(rooms[room]['players'].values()) and not rooms[room]['game_started']:
                    rooms[room]['game_started'] = True
                    await broadcast_message(room, {'type': 'game_started'})
                    print(f"Game started in room {room}")
                    await asyncio.create_task(game_loop(room))
                else:
                    await broadcast_message(room, {'type': 'waiting_for_players'})

            elif message['type'] == 'player_update':
                player = message['player']
                position = message['position']
                rooms[room]['game_state'][player] = position
                await broadcast_message(room, {
                    'type': 'game_state',
                    **rooms[room]['game_state']
                })

    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected for room {room}: {e.code}")
    except Exception as e:
        print(f"WebSocket error in room {room}: {e}")
    finally:
        if room in rooms and websocket in rooms[room]['websockets']:
            rooms[room]['websockets'].remove(websocket)
            print(f"WebSocket removed from room {room}")

            # Clean up the room if no more websockets are left
            if not rooms[room]['websockets']:
                del rooms[room]
                print(f"Room {room} deleted")


async def broadcast_message(room: str, message: dict):
    websockets_to_remove = []
    for ws in rooms[room]['websockets']:
        if ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"Failed to send message to client in room {room}: {e}")
                websockets_to_remove.append(ws)
        else:
            websockets_to_remove.append(ws)

    # Удаление отключенных веб-сокетов
    for ws in websockets_to_remove:
        rooms[room]['websockets'].remove(ws)


async def update_game_state(room: str):
    game_state = rooms[room]['game_state']
    ball = game_state['ball']
    player1 = game_state['player1']
    player2 = game_state['player2']

    # Update ball position
    ball['x'] += ball['dx']
    ball['y'] += ball['dy']

    # Print ball position for debugging
    print(f"Ball position: x={ball['x']}, y={ball['y']}")

    # Reflect off left and right walls
    if ball['x'] - ball['radius'] <= 0 or ball['x'] + ball['radius'] >= canvas_width:
        ball['dx'] = -ball['dx']

    # Reflect off player 1's paddle or give point to player 2
    if ball['y'] - ball['radius'] <= player1['y'] + player1['height']:
        if player1['x'] <= ball['x'] <= player1['x'] + player1['width']:
            # Ball hits player 1's paddle
            ball['dy'] = -ball['dy']
        else:
            # Player 2 scores if ball misses player 1's paddle
            game_state['scores']['player2'] += 1
            # Reset ball to the center
            ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    # Reflect off player 2's paddle or give point to player 1
    if ball['y'] + ball['radius'] >= player2['y']:
        if player2['x'] <= ball['x'] <= player2['x'] + player2['width']:
            # Ball hits player 2's paddle
            ball['dy'] = -ball['dy']
        else:
            # Player 1 scores if ball misses player 2's paddle
            game_state['scores']['player1'] += 1
            # Reset ball to the center
            ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    print(f"Updated game state: {game_state}")

    # Broadcast updated game state to all players in the room
    await broadcast_message(room, {'type': 'game_state', **game_state})



async def game_loop(room: str):
    print(f"Starting game loop for room: {room}")
    try:
        while room in rooms and rooms[room]['game_started']:
            await update_game_state(room)
            await asyncio.sleep(0.033)   # 60 кадров в секунду
    except Exception as e:
        print(f"Error in game loop for room {room}: {e}")
    finally:
        if room in rooms:
            rooms[room]['game_started'] = False
        print(f"Game loop for room {room} ended")

@app.get("/game.html")
async def get_game_html():
    return HTMLResponse(open('static/game.html', 'r').read())

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info", ws_ping_interval=20, ws_ping_timeout=30)
    server = uvicorn.Server(config)
    server.run()