# app.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
from enum import Enum

# --- Implementação das Classes FIEL ao Diagrama UML ---

class Cor(Enum):
    VERMELHO = "red"
    AZUL = "blue"
    VERDE = "green"
    AMARELO = "yellow"
    PRETO = "black"
    BRANCO = "white"
    ROXO = "purple"
    LARANJA = "orange"
    LOCOMOTIVA = "multicolor"
    CINZA = "grey"

# Classe abstrata base
class Carta:
    def descrever(self):
        raise NotImplementedError
    def to_dict(self):
        raise NotImplementedError

class CartaVagao(Carta):
    def __init__(self, cor: Cor):
        self.cor = cor
    def descrever(self):
        return f"Carta de Vagão {self.cor.name}"
    def to_dict(self):
        return {'tipo': 'vagao', 'cor': self.cor.value}

class Cidade:
    def __init__(self, nome: str):
        self._nome = nome
    @property
    def nome(self):
        return self._nome
    def __eq__(self, other):
        return isinstance(other, Cidade) and self._nome == other._nome
    def __hash__(self):
        return hash(self._nome)

class CartaDestino(Carta):
    def __init__(self, origem: Cidade, destino: Cidade, pontos: int):
        self.origem = origem
        self.destino = destino
        self.pontos = pontos
    def descrever(self):
        return f"Objetivo: de {self.origem.nome} para {self.destino.nome} ({self.pontos} pts)"
    def to_dict(self):
        return {'tipo': 'destino', 'origem': self.origem.nome, 'destino': self.destino.nome, 'pontos': self.pontos}

class Baralho:
    def __init__(self, cartas: list[Carta]):
        self._cartas = cartas
        self._descarte = []
        self.embaralhar()

    def embaralhar(self):
        random.shuffle(self._cartas)

    def comprar_carta(self) -> Carta | None:
        if not self._cartas:
            if not self._descarte:
                return None
            self._cartas = self._descarte
            self._descarte = []
            self.embaralhar()
        return self._cartas.pop(0)

    def descartar(self, carta: Carta):
        self._descarte.append(carta)

    def to_dict(self):
        return {'tamanho_baralho': len(self._cartas), 'tamanho_descarte': len(self._descarte)}

class Jogador:
    def __init__(self, sid: str, nome: str, cor: Cor):
        self.sid = sid
        self.nome = nome
        self.cor = cor
        self.pontos = 0
        self.pecas_vagao = 45
        self.cartas_vagao: list[CartaVagao] = []
        self.cartas_destino: list[CartaDestino] = []

    def comprar_carta_vagao(self, carta: CartaVagao):
        self.cartas_vagao.append(carta)

    def comprar_carta_destino(self, cartas: list[CartaDestino]):
        self.cartas_destino.extend(cartas)
    
    def atualizar_pontos(self, pontos: int):
        self.pontos += pontos

    def reivindicar_rota(self, rota: 'Rota', cartas_pagamento: list[CartaVagao]):
        if len(cartas_pagamento) != rota.comprimento:
            return False, "Número incorreto de cartas."
        if self.pecas_vagao < rota.comprimento:
            return False, "Você não tem peças de vagão suficientes."

        locomotivas = [c for c in cartas_pagamento if c.cor == Cor.LOCOMOTIVA]
        cartas_normais = [c for c in cartas_pagamento if c.cor != Cor.LOCOMOTIVA]
        
        cor_rota = rota.cor

        if cor_rota != Cor.CINZA:
            for carta in cartas_normais:
                if carta.cor != cor_rota:
                    return False, f"Para esta rota, você só pode usar cartas da cor {cor_rota.name} ou Locomotivas."
        
        else: # Rota CINZA
            if len(cartas_normais) > 1:
                primeira_cor = cartas_normais[0].cor
                for i in range(1, len(cartas_normais)):
                    if cartas_normais[i].cor != primeira_cor:
                        return False, "Para rotas cinzas, todas as cartas devem ser da mesma cor (além das Locomotivas)."

        for carta_paga in cartas_pagamento:
            self.cartas_vagao.remove(carta_paga)
        
        rota.set_dono(self)
        self.pecas_vagao -= rota.comprimento
        self.atualizar_pontos(rota.calcular_pontos())
        
        return True, "Rota reivindicada com sucesso!"

    def to_dict(self, para_si_mesmo=False):
        d = {
            'sid': self.sid, 'nome': self.nome, 'cor': self.cor.value,
            'pontos': self.pontos, 'pecas_vagao': self.pecas_vagao,
            'num_cartas_vagao': len(self.cartas_vagao),
            'num_cartas_destino': len(self.cartas_destino)
        }
        if para_si_mesmo:
            d['cartas_vagao'] = [c.to_dict() for c in self.cartas_vagao]
        return d

class Rota:
    def __init__(self, cidadeA: Cidade, cidadeB: Cidade, comprimento: int, cor: Cor):
        self.cidadeA = cidadeA
        self.cidadeB = cidadeB
        self.comprimento = comprimento
        self.cor = cor
        self._dono: Jogador | None = None

    def get_dono(self) -> Jogador | None:
        return self._dono

    def set_dono(self, jogador: Jogador):
        self._dono = jogador

    def calcular_pontos(self) -> int:
        pontos_map = {1: 1, 2: 2, 3: 4, 4: 7, 5: 10, 6: 15}
        return pontos_map.get(self.comprimento, 0)

    def to_dict(self):
        return {
            'cidadeA': self.cidadeA.nome, 'cidadeB': self.cidadeB.nome,
            'comprimento': self.comprimento, 'cor': self.cor.value,
            'dono_id': self._dono.sid if self._dono else None
        }

class Tabuleiro:
    def __init__(self):
        self.cidades, self.rotas = self._criar_mapa()

    def get_rota(self, nome_cidade_a: str, nome_cidade_b: str) -> Rota | None:
        for rota in self.rotas:
            if (rota.cidadeA.nome == nome_cidade_a and rota.cidadeB.nome == nome_cidade_b) or \
               (rota.cidadeA.nome == nome_cidade_b and rota.cidadeB.nome == nome_cidade_a):
                return rota
        return None

    def _criar_mapa(self):
        ny = Cidade("Nova York")
        chi = Cidade("Chicago")
        la = Cidade("Los Angeles")
        mia = Cidade("Miami")
        cidades = [ny, chi, la, mia]
        rotas = [
            Rota(ny, chi, 3, Cor.AZUL), Rota(chi, la, 5, Cor.AMARELO),
            Rota(la, mia, 6, Cor.VERDE), Rota(ny, mia, 4, Cor.VERMELHO),
            Rota(chi, mia, 4, Cor.CINZA)
        ]
        return cidades, rotas
    
    def to_dict(self):
        return {
            'cidades': [c.nome for c in self.cidades],
            'rotas': [r.to_dict() for r in self.rotas]
        }

# --- Classe Principal de Gerenciamento do Jogo ---
class Jogo:
    def __init__(self):
        self.jogadores: dict[str, Jogador] = {}
        self.ordem_jogadores: list[str] = []
        self.jogador_da_vez_idx = 0
        self.tabuleiro = Tabuleiro()
        self.baralho_vagao = self._criar_baralho_vagao()
        self.cartas_visiveis: list[CartaVagao] = []
        self.estado = "AGUARDANDO_JOGADORES"
        self.acao_do_turno = {'tipo': None, 'cartas_compradas': 0}
        self.vencedor = None

    def _criar_baralho_vagao(self):
        cartas = []
        cores_normais = [Cor.VERMELHO, Cor.AZUL, Cor.VERDE, Cor.AMARELO, Cor.PRETO, Cor.BRANCO, Cor.ROXO, Cor.LARANJA]
        for cor in cores_normais:
            cartas.extend([CartaVagao(cor) for _ in range(12)])
        cartas.extend([CartaVagao(Cor.LOCOMOTIVA) for _ in range(14)])
        return Baralho(cartas)
    
    def adicionar_jogador(self, sid, nome):
        if len(self.jogadores) >= 4: return None
        cores = [Cor.VERMELHO, Cor.AZUL, Cor.VERDE, Cor.AMARELO]
        cor_usada = [j.cor.value for j in self.jogadores.values()]
        cor_jogador = next(c for c in cores if c.value not in cor_usada)
        novo_jogador = Jogador(sid, nome, cor_jogador)
        self.jogadores[sid] = novo_jogador
        self.ordem_jogadores.append(sid)
        return novo_jogador

    def iniciar_jogo(self):
        if len(self.jogadores) < 2 or self.estado != "AGUARDANDO_JOGADORES": return
        for sid in self.ordem_jogadores:
            jogador = self.jogadores[sid]
            for _ in range(4):
                jogador.comprar_carta_vagao(self.baralho_vagao.comprar_carta())
        self.cartas_visiveis = [self.baralho_vagao.comprar_carta() for _ in range(5)]
        self.estado = "EM_ANDAMENTO"

    def proximo_turno(self):
        self.jogador_da_vez_idx = (self.jogador_da_vez_idx + 1) % len(self.ordem_jogadores)
        self.acao_do_turno = {'tipo': None, 'cartas_compradas': 0}
    
    def get_jogador_da_vez(self) -> Jogador | None:
        if not self.ordem_jogadores or self.estado != "EM_ANDAMENTO":
            return None
        sid_da_vez = self.ordem_jogadores[self.jogador_da_vez_idx]
        return self.jogadores[sid_da_vez]
    
    def _verificar_fim_de_jogo(self):
        todas_reivindicadas = all(rota.get_dono() is not None for rota in self.tabuleiro.rotas)
        if todas_reivindicadas:
            self.estado = "FINALIZADO"
            self._calcular_vencedor()
            return True
        return False

    def _calcular_vencedor(self):
        if not self.jogadores:
            return
        maior_pontuacao = -1
        for jogador in self.jogadores.values():
            if jogador.pontos > maior_pontuacao:
                maior_pontuacao = jogador.pontos
        vencedores = [j for j in self.jogadores.values() if j.pontos == maior_pontuacao]
        self.vencedor = [v.to_dict() for v in vencedores]

    def get_estado_para_frontend(self, para_sid=None):
        jogador_da_vez = self.get_jogador_da_vez()
        return {
            'estado': self.estado,
            'jogadores': [j.to_dict(para_si_mesmo=(j.sid == para_sid)) for j in self.jogadores.values()],
            'tabuleiro': self.tabuleiro.to_dict(),
            'cartas_visiveis': [c.to_dict() for c in self.cartas_visiveis if c],
            'jogador_da_vez_sid': jogador_da_vez.sid if jogador_da_vez else None,
            'acao_do_turno': self.acao_do_turno,
            'vencedor': self.vencedor
        }

# --- Configuração do Servidor Flask e SocketIO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key!'
socketio = SocketIO(app)
jogo = Jogo()

@app.route('/')
def index():
    return render_template('index.html')

def broadcast_game_state():
    for sid in jogo.jogadores:
        emit('game_state_update', jogo.get_estado_para_frontend(para_sid=sid), room=sid)

@socketio.on('connect')
def handle_connect():
    emit('game_state_update', jogo.get_estado_para_frontend(para_sid=request.sid))

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in jogo.jogadores:
        del jogo.jogadores[request.sid]
        if request.sid in jogo.ordem_jogadores:
            jogo.ordem_jogadores.remove(request.sid)
        broadcast_game_state()

@socketio.on('entrar_no_jogo')
def handle_join_game(data):
    nome_jogador = data.get('nome', 'Anônimo')
    if jogo.adicionar_jogador(request.sid, nome_jogador):
        broadcast_game_state()

@socketio.on('iniciar_jogo')
def handle_start_game():
    if request.sid == jogo.ordem_jogadores[0]:
        jogo.iniciar_jogo()
        broadcast_game_state()

@socketio.on('comprar_carta')
def handle_buy_card(data):
    jogador = jogo.get_jogador_da_vez()
    if not jogador or jogador.sid != request.sid:
        return emit('erro_acao', {'motivo': 'Não é sua vez.'})

    index_carta = data['index']
    if jogo.acao_do_turno['cartas_compradas'] == 1 and index_carta != -1:
        carta_alvo = jogo.cartas_visiveis[index_carta]
        if carta_alvo and carta_alvo.cor == Cor.LOCOMOTIVA:
            return emit('erro_acao', {'motivo': 'Você não pode pegar uma Locomotiva como segunda carta.'})

    if jogo.acao_do_turno['tipo'] is None:
        jogo.acao_do_turno['tipo'] = 'COMPRANDO_CARTAS'
    elif jogo.acao_do_turno['tipo'] != 'COMPRANDO_CARTAS':
        return emit('erro_acao', {'motivo': 'Você não pode comprar cartas depois de outra ação.'})

    carta_comprada = None
    era_locomotiva_visivel = False
    if index_carta == -1:
        carta_comprada = jogo.baralho_vagao.comprar_carta()
    elif 0 <= index_carta < len(jogo.cartas_visiveis):
        carta_comprada = jogo.cartas_visiveis[index_carta]
        if carta_comprada.cor == Cor.LOCOMOTIVA:
            era_locomotiva_visivel = True
        jogo.cartas_visiveis[index_carta] = jogo.baralho_vagao.comprar_carta()
    
    if not carta_comprada:
        return emit('erro_acao', {'motivo': 'Carta inválida ou baralho vazio.'})

    jogador.comprar_carta_vagao(carta_comprada)
    jogo.acao_do_turno['cartas_compradas'] += 1

    terminou_o_turno = False
    if jogo.acao_do_turno['cartas_compradas'] >= 2:
        terminou_o_turno = True
    if era_locomotiva_visivel and jogo.acao_do_turno['cartas_compradas'] == 1:
        terminou_o_turno = True
    
    if terminou_o_turno:
        jogo.proximo_turno()
    
    broadcast_game_state()

@socketio.on('reivindicar_rota')
def handle_claim_route(data):
    if jogo.acao_do_turno['tipo'] is not None:
        return emit('erro_acao', {'motivo': 'Você não pode reivindicar uma rota agora.'})
        
    jogador = jogo.get_jogador_da_vez()
    if not jogador or jogador.sid != request.sid:
        return emit('erro_acao', {'motivo': 'Não é sua vez.'})
    
    rota_info = data['rota']
    rota = jogo.tabuleiro.get_rota(rota_info['cidadeA'], rota_info['cidadeB'])
    if not rota or rota.get_dono():
        return emit('erro_acao', {'motivo': 'Rota inválida ou já reivindicada.'})
    
    cartas_pagamento_dict = data['cartas']
    cartas_pagamento_obj = []
    copia_mao = list(jogador.cartas_vagao)
    valido = True
    for cor_val, qtd in cartas_pagamento_dict.items():
        for _ in range(qtd):
            cor_enum = Cor(cor_val)
            carta_encontrada = next((c for c in copia_mao if c.cor == cor_enum), None)
            if carta_encontrada:
                cartas_pagamento_obj.append(carta_encontrada)
                copia_mao.remove(carta_encontrada)
            else:
                valido = False; break
        if not valido: break

    if not valido:
        return emit('erro_acao', {'motivo': 'Você não possui as cartas selecionadas.'})

    sucesso, motivo = jogador.reivindicar_rota(rota, cartas_pagamento_obj)
    
    if sucesso:
        for carta in cartas_pagamento_obj:
            jogo.baralho_vagao.descartar(carta)
        
        if not jogo._verificar_fim_de_jogo():
            jogo.proximo_turno()
        
        broadcast_game_state()
    else:
        emit('erro_acao', {'motivo': motivo})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)