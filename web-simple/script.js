document.addEventListener('DOMContentLoaded', () => {
    // --- CONSTANTS ---
    const TRAIN_COLORS = ["RED", "BLUE", "GREEN", "YELLOW", "BLACK", "WHITE", "ORANGE", "PURPLE", "GRAY", "LOCOMOTIVE"];
    const ROUTE_SCORE = { 1: 1, 2: 2, 3: 4, 4: 7, 5: 10, 6: 15 };
    const START_WAGONS = 45;
    const START_TRAINS = 4;

    // --- GAME STATE ---
    let gameState = {};

    // --- DOM ELEMENTS ---
    const boardEl = document.getElementById('board');
    const playersEl = document.getElementById('players');
    const faceUpCardsEl = document.getElementById('face-up-cards');
    const deckPileEl = document.getElementById('deck-pile');
    const logEl = document.getElementById('log');

    // --- GAME LOGIC CLASSES ---
    class Deck {
        constructor() {
            this.cards = [];
            this.discard = [];
            this.face_up = [];
            
            TRAIN_COLORS.forEach(color => {
                const count = color === "LOCOMOTIVE" ? 14 : 12;
                for (let i = 0; i < count; i++) {
                    this.cards.push({ color });
                }
            });
            this.shuffle();
            this._refill_face_up();
        }

        shuffle() {
            for (let i = this.cards.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [this.cards[i], this.cards[j]] = [this.cards[j], this.cards[i]];
            }
        }

        draw() {
            if (this.cards.length === 0) {
                if (this.discard.length === 0) return null;
                this.cards = [...this.discard];
                this.discard = [];
                this.shuffle();
                logAction("Baralho reembaralhado com as cartas de descarte.");
            }
            return this.cards.pop();
        }
        
        take_face_up(idx) {
            const card = this.face_up.splice(idx, 1)[0];
            this._refill_one();
            return card;
        }

        _refill_one() {
            const newCard = this.draw();
            if (newCard) this.face_up.push(newCard);
            this._check_locomotives();
        }

        _refill_face_up() {
            while (this.face_up.length < 5) {
                const card = this.draw();
                if (!card) break;
                this.face_up.push(card);
            }
             this._check_locomotives();
        }
        
        _check_locomotives() {
            const locoCount = this.face_up.filter(c => c.color === 'LOCOMOTIVE').length;
            if (locoCount >= 3) {
                logAction("3+ locomotivas abertas! Reciclando...");
                this.discard.push(...this.face_up);
                this.face_up = [];
                this._refill_face_up();
            }
        }
    }

    // --- CORE GAME FUNCTIONS ---
    async function initGame() {
        const playerNames = prompt("Digite os nomes dos jogadores, separados por vírgula:", "Ana,Bruno").split(',');
        
        const response = await fetch('../data/map_simple.json');
        const mapData = await response.json();

        gameState = {
            players: playerNames.map(name => ({
                name: name.trim(),
                score: 0,
                wagons: START_WAGONS,
                hand: [],
                countColor: function(color) {
                    return this.hand.filter(c => c.color === color).length;
                }
            })),
            board: mapData,
            deck: new Deck(),
            turn: 0,
            drawsLeft: 0,
            isGameOver: false,
        };

        // Deal initial cards
        gameState.players.forEach(p => {
            for (let i = 0; i < START_TRAINS; i++) {
                p.hand.push(gameState.deck.draw());
            }
        });

        logAction(`Jogo iniciado com ${playerNames.join(', ')}.`);
        renderAll();
    }

    function nextTurn() {
        gameState.turn = (gameState.turn + 1) % gameState.players.length;
        logAction(`É a vez de ${currentPlayer().name}.`);
        renderAll();
    }

    function currentPlayer() {
        return gameState.players[gameState.turn];
    }
    
    function logAction(message) {
        logEl.innerHTML += `<p>${message}</p>`;
        logEl.scrollTop = logEl.scrollHeight;
    }

    // --- RENDER FUNCTIONS ---
    function renderAll() {
        renderBoard();
        renderPlayers();
        renderCards();
    }

    function renderBoard() {
        boardEl.innerHTML = ''; // Clear board
        const cityCoords = {};

        // Draw cities
        gameState.board.cities.forEach(city => {
            const cityEl = document.createElement('div');
            cityEl.className = 'city';
            cityEl.style.left = `${city.x}%`;
            cityEl.style.top = `${city.y}%`;
            
            const nameEl = document.createElement('div');
            nameEl.className = 'city-name';
            nameEl.textContent = city.name;
            nameEl.style.left = `${city.x}%`;
            nameEl.style.top = `${city.y}%`;
            
            boardEl.appendChild(cityEl);
            boardEl.appendChild(nameEl);
            cityCoords[city.name] = { x: city.x, y: city.y };
        });

        // Draw routes
        gameState.board.routes.forEach((route, index) => {
            const posA = cityCoords[route.a];
            const posB = cityCoords[route.b];
            
            const dx = posB.x - posA.x;
            const dy = posB.y - posA.y;
            const length = Math.sqrt(dx*dx + dy*dy);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;

            const routeEl = document.createElement('div');
            routeEl.className = 'route';
            routeEl.style.left = `${posA.x}%`;
            routeEl.style.top = `${posA.y}%`;
            routeEl.style.width = `${length}%`;
            routeEl.style.height = '15px';
            routeEl.style.transformOrigin = '0 50%';
            routeEl.style.transform = `translate(10px, 10px) rotate(${angle}deg)`;
            routeEl.dataset.routeIndex = index;

            if (route.owner !== undefined) {
                 const ownerColor = ['#d32f2f', '#1976d2', '#388e3c', '#fbc02d'][route.owner];
                 routeEl.style.backgroundColor = ownerColor;
                 routeEl.style.border = `2px solid ${ownerColor}`;
            } else {
                 routeEl.style.backgroundColor = 'rgba(128, 128, 128, 0.7)';
            }
            
            const infoEl = document.createElement('span');
            infoEl.className = `route-info card ${route.color}`;
            infoEl.textContent = route.length;
            routeEl.appendChild(infoEl);
            
            routeEl.addEventListener('click', () => handleClaimRoute(index));
            boardEl.appendChild(routeEl);
        });
    }

    function renderPlayers() {
        playersEl.innerHTML = '';
        gameState.players.forEach((player, index) => {
            const pEl = document.createElement('div');
            pEl.className = `player ${index === gameState.turn ? 'active' : ''}`;
            
            let handHtml = '';
            TRAIN_COLORS.forEach(color => {
                const count = player.countColor(color);
                if (count > 0) {
                    handHtml += `<div class="card ${color}" title="${color}">${count}</div>`;
                }
            });

            pEl.innerHTML = `
                <h3>${player.name}</h3>
                <p>Pontos: ${player.score} | Vagões: ${player.wagons}</p>
                <div class="player-hand">${handHtml}</div>
            `;
            playersEl.appendChild(pEl);
        });
    }

    function renderCards() {
        // Face up cards
        faceUpCardsEl.innerHTML = '';
        gameState.deck.face_up.forEach((card, index) => {
            const cardEl = document.createElement('div');
            cardEl.className = `card ${card.color}`;
            cardEl.textContent = card.color;
            cardEl.dataset.index = index;
            cardEl.addEventListener('click', () => handleDrawFaceUp(index));
            faceUpCardsEl.appendChild(cardEl);
        });
        // Deck
        deckPileEl.textContent = `Baralho (${gameState.deck.cards.length})`;
    }

    // --- ACTION HANDLERS ---
    function startDrawAction() {
        if (gameState.drawsLeft > 0) return; // Prevent starting a new action
        gameState.drawsLeft = 2;
        logAction(`${currentPlayer().name} está comprando cartas... (2 restantes)`);
    }
    
    deckPileEl.addEventListener('click', () => {
        if (gameState.drawsLeft === 0) startDrawAction();
        if (gameState.drawsLeft > 0) {
            const card = gameState.deck.draw();
            if (card) {
                currentPlayer().hand.push(card);
                logAction(`${currentPlayer().name} comprou uma carta do baralho.`);
                gameState.drawsLeft--;
            } else {
                logAction("O baralho acabou!");
            }
            if (gameState.drawsLeft === 0) nextTurn();
            else {
                logAction(`Ainda resta 1 compra.`);
                renderAll();
            }
        }
    });

    function handleDrawFaceUp(index) {
        if (gameState.drawsLeft === 0) startDrawAction();
        
        const card = gameState.deck.face_up[index];
        if (card.color === 'LOCOMOTIVE' && gameState.drawsLeft === 1) {
            logAction("Você não pode pegar uma Locomotiva como sua segunda carta.");
            return;
        }

        const drawnCard = gameState.deck.take_face_up(index);
        currentPlayer().hand.push(drawnCard);
        logAction(`${currentPlayer().name} pegou um(a) ${drawnCard.color} das cartas abertas.`);
        
        if (drawnCard.color === 'LOCOMOTIVE') {
            gameState.drawsLeft = 0; // Action ends immediately
        } else {
            gameState.drawsLeft--;
        }

        if (gameState.drawsLeft === 0) nextTurn();
        else {
             logAction(`Ainda resta 1 compra.`);
             renderAll();
        }
    }

    function handleClaimRoute(routeIndex) {
        if (gameState.drawsLeft > 0) {
            logAction("Termine sua ação de comprar cartas primeiro!");
            return;
        }

        const player = currentPlayer();
        const route = gameState.board.routes[routeIndex];

        if (route.owner !== undefined) {
            logAction("Esta rota já tem um dono.");
            return;
        }
        if (player.wagons < route.length) {
            logAction("Você não tem vagões suficientes.");
            return;
        }

        const neededColor = route.color;
        const neededLength = route.length;
        let colorToUse = neededColor;

        if (neededColor === 'GRAY') {
            // Find best color player has
            const availableColors = TRAIN_COLORS
                .filter(c => c !== 'LOCOMOTIVE')
                .filter(c => player.countColor(c) + player.countColor('LOCOMOTIVE') >= neededLength)
                .sort((a,b) => player.countColor(b) - player.countColor(a));
            
            if (availableColors.length === 0) {
                logAction("Você não tem cartas suficientes de nenhuma cor para esta rota cinza.");
                return;
            }
            colorToUse = availableColors[0];
        }

        const colorCards = player.hand.filter(c => c.color === colorToUse);
        const locoCards = player.hand.filter(c => c.color === 'LOCOMOTIVE');

        if (colorCards.length + locoCards.length < neededLength) {
            logAction(`Cartas insuficientes. Precisa de ${neededLength} de ${colorToUse}.`);
            return;
        }

        // Remove cards
        let cardsToRemove = neededLength;
        const newHand = [...player.hand];
        
        for (let i = 0; i < colorCards.length && cardsToRemove > 0; i++) {
            const idx = newHand.findIndex(c => c.color === colorToUse);
            gameState.deck.discard.push(newHand.splice(idx, 1)[0]);
            cardsToRemove--;
        }
        for (let i = 0; i < locoCards.length && cardsToRemove > 0; i++) {
            const idx = newHand.findIndex(c => c.color === 'LOCOMOTIVE');
            gameState.deck.discard.push(newHand.splice(idx, 1)[0]);
            cardsToRemove--;
        }
        player.hand = newHand;
        
        // Update player state
        player.wagons -= neededLength;
        const scoreGained = ROUTE_SCORE[neededLength] || 0;
        player.score += scoreGained;
        route.owner = gameState.turn;

        logAction(`${player.name} conquistou a rota ${route.a}-${route.b}! (+${scoreGained} pts)`);
        nextTurn();
    }

    // --- START GAME ---
    initGame();
});