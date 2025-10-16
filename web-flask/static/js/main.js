// static/js/main.js
document.addEventListener("DOMContentLoaded", () => {
  const socket = io()

  // Elementos da UI
  const loginArea = document.getElementById("login-area")
  const gameArea = document.getElementById("game-info")
  const joinButton = document.getElementById("join-game-btn")
  const nameInput = document.getElementById("player-name")
  const startButton = document.getElementById("start-game-btn")
  const gameStatus = document.getElementById("game-status")
  const turnInfo = document.getElementById("turn-info")
  const playerList = document.getElementById("player-list")
  const myCardsDiv = document.getElementById("my-cards")
  const visibleCardsDiv = document.getElementById("visible-cards")
  const deckBaralho = document.getElementById("deck-baralho")
  const boardContainer = document.getElementById("board-container")
  const errorMessage = document.getElementById("error-message")

  let mySessionId = null
  let selectedHandCards = new Set()

  const cityPositions = {
    "Nova York": { x: 800, y: 150 },
    Chicago: { x: 550, y: 200 },
    "Los Angeles": { x: 100, y: 350 },
    Miami: { x: 750, y: 550 },
  }

  // --- Tratamento de Conexão e Eventos do Servidor ---
  socket.on("connect", () => {
    mySessionId = socket.id
  })

  socket.on("game_state_update", (state) => {
    console.log("Novo estado:", state)
    updateUI(state)
  })

  socket.on("erro_acao", (data) => {
    errorMessage.textContent = data.motivo
    setTimeout(() => (errorMessage.textContent = ""), 3000)
  })

  // --- Lógica de Eventos da UI ---
  joinButton.addEventListener("click", () => {
    const playerName = nameInput.value || "Anônimo"
    socket.emit("entrar_no_jogo", { nome: playerName })
    loginArea.style.display = "none"
    gameArea.style.display = "block"
  })

  startButton.addEventListener("click", () => socket.emit("iniciar_jogo"))

  deckBaralho.addEventListener("click", () => {
    socket.emit("comprar_carta", { index: -1 })
  })

  // --- Funções de Renderização e Lógica ---
  function updateUI(state) {
    const myTurn = state.jogador_da_vez_sid === mySessionId
    const acao = state.acao_do_turno

    const winnerBanner = document.getElementById("winner-banner")
    if (state.estado === "FINALIZADO" && state.vencedor) {
      let winnerText = ""
      if (state.vencedor.length > 1) {
        winnerText = `EMPATE! Vencedores: ${state.vencedor
          .map((v) => v.nome)
          .join(", ")} com ${state.vencedor[0].pontos} pontos!`
      } else {
        winnerText = `FIM DE JOGO! O vencedor é ${state.vencedor[0].nome} com ${state.vencedor[0].pontos} pontos!`
      }
      winnerBanner.textContent = winnerText
      winnerBanner.classList.remove("hidden")
      turnInfo.style.display = "none"
    } else {
      winnerBanner.classList.add("hidden")
    }

    turnInfo.style.fontWeight = "bold"
    if (myTurn) {
      if (acao.tipo === "COMPRANDO_CARTAS" && acao.cartas_compradas === 1) {
        turnInfo.textContent = "É a sua vez! Compre sua segunda carta."
        turnInfo.style.color = "blue"
      } else {
        turnInfo.textContent = "É a sua vez! Escolha sua ação."
        turnInfo.style.color = "green"
      }
    } else {
      turnInfo.textContent = "Aguarde sua vez."
      turnInfo.style.color = "black"
    }

    gameStatus.textContent = `Estado: ${state.estado.replace("_", " ")}`
    const souPrimeiroJogador =
      state.jogadores.length > 0 && state.jogadores[0].sid === mySessionId
    startButton.style.display =
      state.estado === "AGUARDANDO_JOGADORES" && souPrimeiroJogador
        ? "block"
        : "none"

    playerList.innerHTML = ""
    state.jogadores.forEach((p) => {
      const li = document.createElement("li")
      li.style.backgroundColor = p.cor
      li.style.color = "white"
      li.textContent = `[${p.nome}] Pts: ${p.pontos} / Vagões: ${p.pecas_vagao}`
      if (
        p.sid === state.jogador_da_vez_sid &&
        state.estado === "EM_ANDAMENTO"
      ) {
        li.classList.add("active-turn")
      }
      playerList.appendChild(li)
    })

    const myPlayerData = state.jogadores.find((p) => p.sid === mySessionId)
    if (myPlayerData && myPlayerData.cartas_vagao) {
      renderHand(myPlayerData.cartas_vagao)
    }

    renderVisibleCards(state.cartas_visiveis, myTurn, acao, state.estado)
    renderBoard(state.tabuleiro, state.jogadores, myTurn, acao, state.estado)
  }

  function renderCard(cardData, isHandCard = false) {
    const cardDiv = document.createElement("div")
    cardDiv.classList.add("card")
    cardDiv.dataset.cor = cardData.cor
    cardDiv.style.backgroundColor = cardData.cor
    if (cardData.cor === "multicolor") {
      cardDiv.classList.add("card-multicolor")
    }
    cardDiv.textContent = cardData.cor.toUpperCase()

    if (isHandCard) {
      cardDiv.addEventListener("click", () => toggleCardSelection(cardDiv))
    }
    return cardDiv
  }

  function renderHand(cards) {
    myCardsDiv.innerHTML = ""
    cards.forEach((card, index) => {
      const cardDiv = renderCard(card, true)
      cardDiv.dataset.index = index
      if (selectedHandCards.has(cardDiv)) {
        cardDiv.classList.add("selected")
      }
      myCardsDiv.appendChild(cardDiv)
    })
  }

  function renderVisibleCards(cards, myTurn, acao, estadoJogo) {
    visibleCardsDiv.innerHTML = ""
    cards.forEach((card, index) => {
      const cardDiv = renderCard(card)

      const podeIniciarCompra =
        myTurn && acao.tipo === null && estadoJogo === "EM_ANDAMENTO"
      const podeContinuarCompra =
        myTurn &&
        acao.tipo === "COMPRANDO_CARTAS" &&
        acao.cartas_compradas === 1

      const ehLocomotiva = card.cor === "multicolor"
      const ehSegundaCompra = podeContinuarCompra

      const podeClicar =
        podeIniciarCompra || (podeContinuarCompra && !ehLocomotiva)

      if (podeClicar) {
        cardDiv.style.cursor = "pointer"
        cardDiv.onclick = () => socket.emit("comprar_carta", { index })
      } else {
        cardDiv.style.cursor = "not-allowed"
      }
      visibleCardsDiv.appendChild(cardDiv)
    })
  }

  function renderBoard(tabuleiro, jogadores, myTurn, acao, estadoJogo) {
    boardContainer.innerHTML = ""
    tabuleiro.rotas.forEach((r) => {
      const posA = cityPositions[r.cidadeA]
      const posB = cityPositions[r.cidadeB]

      const dx = posB.x - posA.x
      const dy = posB.y - posA.y
      const length = Math.sqrt(dx * dx + dy * dy)
      const angle = (Math.atan2(dy, dx) * 180) / Math.PI

      const routeDiv = document.createElement("div")
      routeDiv.classList.add("route")
      routeDiv.style.width = `${length}px`
      routeDiv.style.left = `${posA.x}px`
      routeDiv.style.top = `${posA.y - 5}px`
      routeDiv.style.transform = `rotate(${angle}deg)`

      for (let i = 0; i < r.comprimento; i++) {
        const segment = document.createElement("div")
        segment.classList.add("route-segment")
        segment.style.backgroundColor = r.cor
        routeDiv.appendChild(segment)
      }

      if (r.dono_id) {
        const dono = jogadores.find((j) => j.sid === r.dono_id)
        routeDiv.style.border = `3px solid ${dono.cor}`
        routeDiv.style.opacity = "1"
      } else {
        routeDiv.style.opacity = "0.7"
        const podeReivindicar =
          myTurn && acao.tipo === null && estadoJogo === "EM_ANDAMENTO"
        if (podeReivindicar) {
          routeDiv.style.cursor = "pointer"
          routeDiv.onclick = () => tryClaimRoute(r)
        } else {
          routeDiv.style.cursor = "not-allowed"
        }
      }
      boardContainer.appendChild(routeDiv)
    })

    tabuleiro.cidades.forEach((nome) => {
      const pos = cityPositions[nome]
      const cityDiv = document.createElement("div")
      cityDiv.classList.add("city")
      cityDiv.style.left = `${pos.x - 10}px`
      cityDiv.style.top = `${pos.y - 10}px`

      const nameDiv = document.createElement("div")
      nameDiv.classList.add("city-name")
      nameDiv.textContent = nome
      cityDiv.appendChild(nameDiv)

      boardContainer.appendChild(cityDiv)
    })
  }

  function toggleCardSelection(cardDiv) {
    if (selectedHandCards.has(cardDiv)) {
      selectedHandCards.delete(cardDiv)
      cardDiv.classList.remove("selected")
    } else {
      selectedHandCards.add(cardDiv)
      cardDiv.classList.add("selected")
    }
  }

  function tryClaimRoute(rota) {
    if (selectedHandCards.size === 0) {
      alert("Selecione cartas da sua mão para reivindicar uma rota.")
      return
    }

    const cartasParaUsar = {}
    selectedHandCards.forEach((cardDiv) => {
      const cor = cardDiv.dataset.cor
      cartasParaUsar[cor] = (cartasParaUsar[cor] || 0) + 1
    })

    selectedHandCards.forEach((c) => c.classList.remove("selected"))
    selectedHandCards.clear()

    socket.emit("reivindicar_rota", { rota, cartas: cartasParaUsar })
  }
})
