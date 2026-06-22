from src.services.city_data_service import carregar_bestiario_cidade, carregar_inimigos_cidade
from src.services.database import salvar_json


PLAYER_PATH = "data/core/player.json"


def _obter_cidade(player):
    if isinstance(player, dict):
        return player.get("current_location", "phandalin")
    return str(player or "phandalin")


def carregar_inimigos(player):
    return carregar_inimigos_cidade(_obter_cidade(player))


def carregar_bestiario_base(player):
    return carregar_bestiario_cidade(_obter_cidade(player))


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
    inimigos = carregar_inimigos(player)
    lore = carregar_bestiario_base(player)

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
