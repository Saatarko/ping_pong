let canvas = document.getElementById('gameCanvas');
let ctx = canvas.getContext('2d');
let player1 = { x: 350, y: 10, width: 100, height: 20 };
let player2 = { x: 350, y: 570, width: 100, height: 20 };
let ball = { x: 400, y: 300, radius: 10, dx: 2, dy: -2 };



document.addEventListener('DOMContentLoaded', function () {

    const closeAjaxButton = document.getElementById('close-ajax-popup');
    if (closeAjaxButton) {
        closeAjaxButton.addEventListener('click', function () {
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
    if (playerId === null) return;

    console.log(`Key pressed: ${event.key}, Player ID: ${playerId}`);

    let player;
    if (playerId === 1) {
        player = player1;
    } else if (playerId === 2) {
        player = player2;
    }

    if (event.key === 'ArrowRight') {
        player.x = Math.min(canvas.width - player.width, player.x + 15);
        console.log(`Player ${playerId} moved right`);
    } else if (event.key === 'ArrowLeft') {
        player.x = Math.max(0, player.x - 15);
        console.log(`Player ${playerId} moved left`);
    }

    sendPlayerPosition(); // Отправляем позицию игрока после её изменения
});

function sendPlayerPosition() {
    if (ws && ws.readyState === WebSocket.OPEN && playerId !== null) {
        const position = playerId === 1 ? player1 : player2;
        console.log('Sending player position:', {
            type: 'player_update',
            position: {
                x: position.x,
                y: position.y
            }
        });

        ws.send(JSON.stringify({
            type: 'player_update',
            playerId: playerId, // добавим идентификатор игрока для различия
            position: {
                x: position.x,
                y: position.y
            }
        }));
    }
}

function draw() {
    console.log('Drawing game state:', player1, player2, ball);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'yellow';
    ctx.fillRect(player1.x, player1.y, player1.width, player1.height);
    ctx.fillStyle = 'red';
    ctx.fillRect(player2.x, player2.y, player2.width, player2.height);
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.closePath();
    console.log('Draw complete');
}

function updateScore() {
    console.log('Updating scores:', scorePlayer1, scorePlayer2);
    document.getElementById('scorePlayer1').innerText = `Игрок 1 (желтый): ${scorePlayer1}`;
    document.getElementById('scorePlayer2').innerText = `Игрок 2 (красный): ${scorePlayer2}`;
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
