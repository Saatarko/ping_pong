const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let playerId = null;
let player1 = { x: 350, y: 10, width: 100, height: 20 };
let player2 = { x: 350, y: 570, width: 100, height: 20 };
let ball = { x: 400, y: 300, radius: 10, dx: 2, dy: -2 };
let scorePlayer1 = 0;
let scorePlayer2 = 0;
let gameRunning = false;

let ws = null;

async function createGame() {
    const response = await fetch('/create_game', { method: 'POST' });
    const data = await response.json();
    return data.game_key;
}

function connectWebSocket(gameKey) {
    if (ws) {
        ws.close();
    }

    ws = new WebSocket(`ws://localhost:8000/ws/${gameKey}`);

    ws.onopen = () => {
        console.log('WebSocket connection established');
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed');
    };

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'playerId') {
            playerId = data.playerId;
            console.log('Player ID received:', playerId);
        } else if (data.type === 'player_update') {
            // Обработка обновлений игроков
        } else if (data.type === 'game_state') {
            // Обработка состояния игры
        } else if (data.type === 'game_started') {
            gameRunning = true;
            gameLoop();
        } else if (data.type === 'error') {
            console.error('Error:', data.message);
        }
    };
}

document.addEventListener('DOMContentLoaded', function() {
    const createGameButton = document.getElementById('createGameButton');
    if (createGameButton) {
        createGameButton.addEventListener('click', async function () {
            const gameKey = await createGame();
                        // Устанавливаем значение gameKey в поле ввода с id 'gameKey'
            document.getElementById('gameKey').value = gameKey;

            // Подключаем WebSocket
            connectWebSocket(gameKey);


        });
    }

    const startButton = document.getElementById('startButton');
    if (startButton) {
        startButton.addEventListener('click', function () {
            if (playerId === null) {
                console.log('Player ID is not set yet');
                return;
            }

            ws.send(JSON.stringify({ type: 'start_game' }));
        });
    }

    const closeAjaxButton = document.getElementById('close-ajax-popup');
    if (closeAjaxButton) {
        closeAjaxButton.addEventListener('click', function() {
            const popup = document.getElementById('ajax-popup');
            if (popup) {
                popup.style.opacity = 0;
                setTimeout(() => {
                    popup.style.display = 'none';
                }, 500);
            }
        });
    }
});

document.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowRight') {
        player1.x += 15;
    } else if (event.key === 'ArrowLeft') {
        player1.x -= 15;
    }

    if (gameRunning && playerId !== null && ws !== null) {
        ws.send(JSON.stringify({ type: 'player_update', playerId: playerId, x: player1.x }));
    }
});

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'yellow';
    ctx.fillRect(player1.x, player1.y, player1.width, player1.height);
    ctx.fillStyle = 'red';
    ctx.fillRect(player2.x, player2.y, player2.width, player2.height);
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

function updateGame() {
    if (!gameRunning) return;

    ball.x += ball.dx;
    ball.y += ball.dy;

    if (ball.x + ball.dx > canvas.width - ball.radius || ball.x + ball.dx < ball.radius) {
        ball.dx = -ball.dx;
    }

    if (ball.y + ball.dy < player1.y + player1.height && ball.x > player1.x && ball.x < player1.x + player1.width) {
        ball.dy = -ball.dy;
    } else if (ball.y + ball.dy > player2.y - ball.radius && ball.x > player2.x && ball.x < player2.x + player2.width) {
        ball.dy = -ball.dy;
    }

    if (ball.y + ball.dy > canvas.height - ball.radius) {
        scorePlayer1++;
        if (scorePlayer1 >= 5) {
            showAjaxPopup('Игрок 1 победил!');
            resetGame();
            return;
        }
        ball.x = canvas.width / 2;
        ball.y = canvas.height / 2;
        ball.dy = -2;
    } else if (ball.y + ball.dy < ball.radius) {
        scorePlayer2++;
        if (scorePlayer2 >= 5) {
            showAjaxPopup('Игрок 2 победил!');
            resetGame();
            return;
        }
        ball.x = canvas.width / 2;
        ball.y = canvas.height / 2;
        ball.dy = 2;
    }

    draw();
    updateScore();

    if (gameRunning && playerId !== null && ws !== null) {
        ws.send(JSON.stringify({
            type: 'game_state',
            ball: ball,
            player1: player1,
            player2: player2,
            scorePlayer1: scorePlayer1,
            scorePlayer2: scorePlayer2
        }));
    }
}

function updateScore() {
    document.getElementById('scorePlayer1').innerText = `Игрок 1(желтый): ${scorePlayer1}`;
    document.getElementById('scorePlayer2').innerText = `Игрок 2(красный): ${scorePlayer2}`;
}

function resetGame() {
    scorePlayer1 = 0;
    scorePlayer2 = 0;
    ball.x = canvas.width / 2;
    ball.y = canvas.height / 2;
    ball.dx = 2;
    ball.dy = -2;
    gameRunning = false;
    updateScore();
}

function gameLoop() {
    if (gameRunning) {
        updateGame();
        requestAnimationFrame(gameLoop);
    }
}

function showAjaxPopup(message) {
    const popup = document.getElementById('ajax-popup');
    const popupMessage = document.getElementById('ajax-popup-message');

    if (popup && popupMessage) {
        popupMessage.textContent = message;
        popup.style.display = 'block';

        setTimeout(() => {
            popup.style.opacity = 1;
            setTimeout(() => {
                popup.style.opacity = 0;
                setTimeout(() => {
                    popup.style.display = 'none';
                }, 500);
            }, 3000);
        }, 100);
    }
}
