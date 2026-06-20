from src.services.database import carregar_json, salvar_json


PLAYER_PATH = "data/core/player.json"
ENEMIES_PATH = "data/enemies/enemies.json"
BESTIARY_PATH = "data/core/bestiary.json"


def carregar_inimigos():
    return carregar_json(ENEMIES_PATH) or {}


def carregar_bestiario_base():
    return carregar_json(BESTIARY_PATH) or {}


def garantir_bestiario(player):
    if "bestiary" not in player or not isinstance(player["bestiary"], dict):
        player["bestiary"] = {}
        return True

    return False


def obter_estado_bestiario(player, enemy_id):
    garantir_bestiario(player)
    return player["bestiary"].get(enemy_id, {"seen": 0, "defeated": 0})


def registrar_encontro(player, enemy_id):
    garantir_bestiario(player)
    estado = player["bestiary"].setdefault(enemy_id, {"seen": 0, "defeated": 0})
    estado["seen"] = int(estado.get("seen", 0)) + 1
    salvar_json(PLAYER_PATH, player)
    return estado


def registrar_derrota_inimigo(player, enemy_id):
    garantir_bestiario(player)
    estado = player["bestiary"].setdefault(enemy_id, {"seen": 0, "defeated": 0})
    estado["seen"] = max(1, int(estado.get("seen", 0)))
    estado["defeated"] = int(estado.get("defeated", 0)) + 1
    salvar_json(PLAYER_PATH, player)
    return estado


def listar_entradas_bestiario(player):
    garantir_bestiario(player)
    inimigos = carregar_inimigos()
    lore = carregar_bestiario_base()

    entradas = []
    for enemy_id, dados in inimigos.items():
        estado = obter_estado_bestiario(player, enemy_id)
        conhecido = estado.get("seen", 0) > 0 or estado.get("defeated", 0) > 0
        dominado = estado.get("defeated", 0) > 0
        entradas.append(
            {
                "id": enemy_id,
                "enemy": dados,
                "lore": lore.get(enemy_id, {}),
                "state": estado,
                "known": conhecido,
                "mastered": dominado,
            }
        )

    return entradas
