import json, random, os, sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# --- Constantes (sem alterações) ---
SAVE_PATH = os.path.join(os.path.dirname(__file__), "saves.json")
MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "map_simple.json")

TRAIN_COLORS = ["RED","BLUE","GREEN","YELLOW","BLACK","WHITE","ORANGE","PURPLE","GRAY","LOCOMOTIVE"]
ROUTE_SCORE = {1:1, 2:2, 3:4, 4:7, 5:10, 6:15}
START_WAGONS = 45
START_TRAINS = 4

# --- Classes de Dados (sem alterações) ---
@dataclass
class TrainCard:
    color: str

@dataclass
class City:
    name: str

@dataclass
class Route:
    a: str
    b: str
    color: str
    length: int
    owner: Optional[int] = None

@dataclass
class Player:
    name: str
    wagons: int = START_WAGONS
    score: int = 0
    hand: List[TrainCard] = field(default_factory=list)

    def count_color(self, color: str) -> int:
        return sum(1 for c in self.hand if c.color == color)

    def remove_cards(self, color: str, n: int) -> List[TrainCard]:
        used = []
        hand_copy = self.hand[:]
        # Primeiro, tenta usar as cartas da cor específica
        for _ in range(n):
            card_to_remove = next((c for c in hand_copy if c.color == color), None)
            if card_to_remove:
                used.append(card_to_remove)
                hand_copy.remove(card_to_remove)
        
        # Se ainda faltarem cartas, usa Locomotivas
        remaining_needed = n - len(used)
        for _ in range(remaining_needed):
            loco_to_remove = next((c for c in hand_copy if c.color == "LOCOMOTIVE"), None)
            if loco_to_remove:
                used.append(loco_to_remove)
                hand_copy.remove(loco_to_remove)
            else:
                # Se não houver locomotivas suficientes, a operação falha
                raise ValueError("not enough cards")
        
        # Se chegou até aqui, atualiza a mão real
        self.hand = hand_copy
        return used

# --- Classes de Jogo (com alterações) ---
class Deck:
    def __init__(self, seed: int = 42):
        rnd = random.Random(seed)
        cards = []
        for color in TRAIN_COLORS:
            if color == "LOCOMOTIVE":
                cards += [TrainCard(color)] * 14 # Aumentado para um baralho mais realista
            else:
                cards += [TrainCard(color)] * 12
        rnd.shuffle(cards)
        self._rnd = rnd
        self.cards = cards
        self.discard: List[TrainCard] = []
        self.face_up: List[TrainCard] = []
        self._refill_face_up()

    def draw(self) -> Optional[TrainCard]:
        if not self.cards and not self.discard:
            return None # Fim do baralho
        if not self.cards:
            self.cards = self.discard
            self.discard = []
            self._rnd.shuffle(self.cards)
        return self.cards.pop()

    def take_face_up(self, idx: int) -> TrainCard:
        card = self.face_up.pop(idx)
        self._refill_one()
        return card

    def _refill_one(self):
        new_card = self.draw()
        if new_card:
            self.face_up.append(new_card)
        
        # Regra opcional: se houver 3+ locomotivas, recicla as abertas
        if sum(1 for c in self.face_up if c.color == "LOCOMOTIVE") >= 3:
            print("(!) 3 ou mais locomotivas abertas. Reciclando...")
            self.discard.extend(self.face_up)
            self.face_up = []
            self._refill_face_up()

    def _refill_face_up(self):
        while len(self.face_up) < 5:
            card = self.draw()
            if card is None: break # Para se o baralho acabar
            self.face_up.append(card)

class Board:
    # (sem alterações)
    def __init__(self, data: Dict):
        self.cities = {c["name"]: City(c["name"]) for c in data["cities"]}
        self.routes = [Route(**r) for r in data["routes"]]

    def find_route(self, a: str, b: str) -> Optional[Route]:
        for r in self.routes:
            if (r.a==a and r.b==b) or (r.a==b and r.b==a):
                return r
        return None

class Game:
    # (sem alterações no __init__)
    def __init__(self, names: List[str], seed: int = 42):
        with open(MAP_PATH, 'r') as f:
            data = json.load(f)
        if len(names) < 2:
            raise ValueError("É preciso pelo menos 2 jogadores.")
        self.board = Board(data)
        self.players = [Player(n) for n in names]
        self.turn = 0
        self.deck = Deck(seed)
        for p in self.players:
            for _ in range(START_TRAINS):
                p.hand.append(self.deck.draw())

    def draw_from_deck(self, p: Player):
        card = self.deck.draw()
        if card:
            p.hand.append(card)
            print(f"Você comprou uma carta {card.color} do baralho.")
        else:
            print("O baralho acabou!")

    def draw_face_up(self, p: Player, idx: int):
        if idx < 0 or idx >= len(self.deck.face_up):
            raise IndexError("Índice inválido para cartas abertas (0-4).")
        card = self.deck.face_up[idx]
        if card.color == "LOCOMOTIVE":
             raise ValueError("Você não pode pegar uma Locomotiva como sua primeira carta. Se quiser, pegue-a como uma ação única.")
        p.hand.append(self.deck.take_face_up(idx))
        print(f"Você pegou uma carta {card.color} das abertas.")

    def draw_locomotive(self, p: Player, idx: int):
        if self.deck.face_up[idx].color != "LOCOMOTIVE":
            raise ValueError("Esta ação é apenas para pegar uma Locomotiva aberta.")
        card = self.deck.take_face_up(idx)
        p.hand.append(card)
        print(f"Você pegou uma Locomotiva! Seu turno acabou.")

    # ALTERAÇÃO: Agora retorna um booleano indicando sucesso.
    def claim_route(self, p: Player, a: str, b: str) -> (bool, str):
        r = self.board.find_route(a,b)
        if not r:
            return False, "Rota inexistente"
        if r.owner is not None:
            return False, "Rota já ocupada"
        
        color = r.color
        need = r.length
        
        if p.wagons < need:
            return False, "Vagões insuficientes."

        # rotas cinzas: escolhe a cor mais abundante do jogador
        chosen_color = color
        if color == "GRAY":
            # Filtra cores que o jogador pode usar (tem cartas suficientes)
            possible_colors = []
            for c in TRAIN_COLORS:
                if c == "LOCOMOTIVE": continue
                have_color = p.count_color(c)
                have_loco = p.count_color("LOCOMOTIVE")
                if have_color + have_loco >= need:
                    possible_colors.append((have_color, c))
            
            if not possible_colors:
                return False, "Cartas insuficientes para qualquer cor na rota cinza."

            # Escolhe a cor que o jogador tem em maior quantidade
            best_color = max(possible_colors, key=lambda item: item[0])[1]
            chosen_color = best_color

        have = p.count_color(chosen_color) + p.count_color("LOCOMOTIVE")
        if have < need:
            return False, f"Cartas insuficientes da cor {chosen_color} (precisa: {need}, tem: {have-p.count_color('LOCOMOTIVE')} + {p.count_color('LOCOMOTIVE')} locos)."
        
        try:
            used = p.remove_cards(chosen_color, need)
        except ValueError:
            return False, "Falha ao consumir cartas (erro interno)."
        
        self.deck.discard.extend(used)
        p.wagons -= need
        score_gain = ROUTE_SCORE.get(need, 0)
        p.score += score_gain
        r.owner = self.turn
        return True, f"Rota {a}-{b} reivindicada com {chosen_color}! (+{score_gain} pts)"

    def next_turn(self):
        self.turn = (self.turn + 1) % len(self.players)

def print_state(g: Game):
    p = g.players[g.turn]
    print("\n" + "="*40)
    print(f"Turno de: {p.name} | Pontos: {p.score} | Vagões: {p.wagons}")
    print("-"*40)
    counts = {c: p.count_color(c) for c in TRAIN_COLORS if p.count_color(c) > 0}
    print("Sua Mão:", " ".join([f"{k}:{v}" for k,v in counts.items()]))
    print("Cartas Abertas:", ", ".join([f"[{i}]{c.color}" for i, c in enumerate(g.deck.face_up)]))
    print("Rotas Livres:")
    for r in g.board.routes:
        if r.owner is None:
            print(f"  - {r.a:<12} -> {r.b:<12} | Cor: {r.color:<8} | Tamanho: {r.length}")
    print("="*40)


def main():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(MAP_PATH):
        print("ERRO: map_simple.json não encontrado em data/")
        sys.exit(1)

    print("=== Ticket to Ride – CLI (Corrigido) ===")
    names_raw = input("Nomes dos jogadores (separados por vírgula): ").strip()
    names = [n.strip() for n in names_raw.split(',') if n.strip()]
    
    try:
        g = Game(names)
    except Exception as e:
        print(f"Erro ao iniciar jogo: {e}")
        return

    while True:
        p = g.players[g.turn]
        print_state(g)
        
        # --- LÓGICA DE TURNO CORRIGIDA ---
        action_taken = False
        while not action_taken:
            cmd_raw = input(f"\nAção para {p.name} [d]raw, [c]laim, [q]uit >> ").strip().lower()
            if not cmd_raw: continue

            if cmd_raw == 'd':
                # Lógica para comprar 2 cartas
                print("Escolha sua primeira carta: [d]eck ou [f]ace-up <0-4>?")
                draw1_cmd = input(">> ").strip().split()
                
                try:
                    if draw1_cmd[0] == 'd':
                        g.draw_from_deck(p)
                    elif draw1_cmd[0] == 'f':
                        idx = int(draw1_cmd[1])
                        card = g.deck.face_up[idx]
                        if card.color == "LOCOMOTIVE":
                           g.draw_locomotive(p, idx)
                           action_taken = True # Pegar locomotiva encerra o turno
                           continue
                        else:
                           g.draw_face_up(p, idx)
                    else:
                        print("Comando inválido.")
                        continue # Volta para o prompt de ação
                    
                    # Segunda compra
                    print_state(g)
                    print("Escolha sua segunda carta: [d]eck ou [f]ace-up <0-4>?")
                    draw2_cmd = input(">> ").strip().split()
                    if draw2_cmd[0] == 'd':
                        g.draw_from_deck(p)
                    elif draw2_cmd[0] == 'f':
                        idx = int(draw2_cmd[1])
                        # Na segunda compra, pode pegar locomotiva
                        card = g.deck.take_face_up(idx)
                        p.hand.append(card)
                        print(f"Você pegou uma carta {card.color} das abertas.")
                    
                    action_taken = True

                except (ValueError, IndexError) as e:
                    print(f"Erro na jogada: {e}. Tente novamente.")

            elif cmd_raw.startswith('c'):
                parts = cmd_raw.split()
                if len(parts) < 3:
                    print("Uso: c <CidadeA> <CidadeB>"); 
                    continue
                
                success, msg = g.claim_route(p, parts[1], parts[2])
                print(msg)
                if success:
                    action_taken = True
                # Se não teve sucesso (success=False), o loop continua e o jogador tenta de novo.

            elif cmd_raw == 'q':
                print("Saindo...")
                return # Encerra o programa
            
            else:
                print("Comando desconhecido. Opções: [d]raw, [c]laim <A> <B>, [q]uit")

        g.next_turn()

if __name__ == '__main__':
    main()