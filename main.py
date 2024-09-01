import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json


from starlette.websockets import WebSocketState, WebSocket

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Constants and initial state
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
            'game_started': False,
            'game_loop_task': None
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

                    # Запускаем игровой цикл в фоновом режиме
                    if rooms[room]['game_loop_task'] is not None:
                        rooms[room]['game_loop_task'].cancel()
                    rooms[room]['game_loop_task'] = asyncio.create_task(run_game_loop(room))

            elif message['type'] == 'player_update':
                player = message['player']
                position = message['position']
                rooms[room]['game_state'][player] = position
                await broadcast_message(room, {
                    'type': 'game_state',
                    **rooms[room]['game_state']
                })

    except Exception as e:
        print(f"Exception in websocket handling: {e}")

    finally:
        remove_websocket(room, websocket)


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

    for ws in websockets_to_remove:
        remove_websocket(room, ws)


def remove_websocket(room: str, ws: WebSocket):
    if room in rooms and ws in rooms[room]['websockets']:
        rooms[room]['websockets'].remove(ws)
        print(f"WebSocket removed from room {room}")
        if not rooms[room]['websockets']:
            if rooms[room]['game_loop_task'] is not None:
                rooms[room]['game_loop_task'].cancel()
            del rooms[room]
            print(f"Room {room} deleted")


async def run_game_loop(room: str):
    print(f"Starting game loop for room: {room}")
    try:
        while room in rooms and rooms[room]['game_started']:
            try:
                update_game_state(room)
                # Отправляем обновленное состояние всем подключенным WebSocket
                await broadcast_message(room, rooms[room]['game_state'])
            except Exception as e:
                print(f"Error in update_game_state for room {room}: {e}")
                break
            await asyncio.sleep(1)  # Обновляем раз в 1 секунду

    except Exception as e:
        print(f"Error in game loop for room {room}: {e}")
    finally:
        if room in rooms:
            rooms[room]['game_started'] = False
        print(f"Game loop for room {room} ended")


def update_game_state(room: str):
    game_state = rooms[room]['game_state']
    ball = game_state['ball']
    player1 = game_state['player1']
    player2 = game_state['player2']

    print(f"Updating game state: {game_state}")

    ball['x'] += ball['dx']
    ball['y'] += ball['dy']

    if ball['x'] - ball['radius'] <= 0 or ball['x'] + ball['radius'] >= canvas_width:
        ball['dx'] = -ball['dx']

    if ball['y'] - ball['radius'] <= 0:
        game_state['scores']['player2'] += 1
        ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    if ball['y'] + ball['radius'] >= canvas_height:
        game_state['scores']['player1'] += 1
        ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    if ball['y'] <= player1['y'] + player1['height']:
        if player1['x'] <= ball['x'] <= player1['x'] + player1['width']:
            ball['y'] = player1['y'] + player1['height'] + ball['radius']
            ball['dy'] = -ball['dy']
        else:
            game_state['scores']['player2'] += 1
            ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    if ball['y'] + ball['radius'] >= player2['y']:
        if player2['x'] <= ball['x'] <= player2['x'] + player2['width']:
            ball['y'] = player2['y'] - ball['radius']
            ball['dy'] = -ball['dy']
        else:
            game_state['scores']['player1'] += 1
            ball.update({'x': canvas_width // 2, 'y': canvas_height // 2, 'dx': BALL_SPEED, 'dy': BALL_SPEED})

    print(f"Updated game state: {game_state}")


@app.get("/game.html")
async def get_game_html():
    return HTMLResponse(open('static/game.html', 'r').read())


if __name__ == "__main__":
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info", ws_ping_interval=20, ws_ping_timeout=30)
    server = uvicorn.Server(config)
    server.run()
