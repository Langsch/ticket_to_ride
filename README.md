# 🚂 Ticket to Ride - Implementação Digital

Implementação do jogo de tabuleiro **Ticket to Ride** em diferentes versões: CLI, Web simples e Web com Flask.

## 📁 Estrutura do Projeto

```
ticket_to_ride/
├── README.md                 # Este arquivo
├── .gitignore               # Arquivos ignorados pelo Git
│
├── docs/                    # 📚 Documentação
│   ├── Grupo 3 - Ativ 1 PS.pdf
│   └── diagramas/
│       ├── Diagrama de Classes.puml
│       ├── Diagrama de Sequência.puml
│       └── Diagrama de Comunicação.puml
│
├── data/                    # 🗺️ Dados do jogo
│   └── map_simple.json      # Mapa simplificado de rotas
│
├── cli/                     # 💻 Versão de linha de comando
│   ├── t2r_cli.py          # Jogo CLI interativo
│   └── saves.json          # Arquivos de save (gerado)
│
├── web-simple/              # 🌐 Versão web básica (HTML/CSS/JS)
│   ├── index.html
│   ├── script.js
│   └── style.css
│
└── web-flask/               # 🚀 Versão web completa com Flask
    ├── app.py              # Servidor Flask com SocketIO
    ├── static/
    │   ├── css/
    │   │   └── style.css
    │   └── js/
    │       └── main.js
    └── templates/
        └── index.html
```

## 🎮 Como Jogar

### 1️⃣ Versão CLI (Terminal)

**Requisitos:** Python 3.7+

```bash
cd cli
python t2r_cli.py
```

### 2️⃣ Versão Web Simples

Basta abrir o arquivo `web-simple/index.html` no seu navegador.

### 3️⃣ Versão Web Flask (Multiplayer)

**Requisitos:** Python 3.7+ e dependências

```bash
cd web-flask
pip install flask flask-socketio
python app.py
```

## 📖 Documentação

Os diagramas UML completos estão disponíveis em `docs/diagramas/`:
- **Diagrama de Classes**: Arquitetura completa do sistema e relacionamentos entre entidades
- **Diagrama de Sequência**: Fluxo detalhado de interações para reivindicar rotas
- **Diagrama de Comunicação**: Visão geral da comunicação entre objetos em todos os cenários do jogo

## 👥 Autores

Rafael Valverde  
Paulo Carrano  
Jansen Alves  
Rafael Langsch  

---