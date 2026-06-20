import random

from src.services.database import salvar_json


PLAYER_PATH = "data/core/player.json"
EQUIPMENT_SLOTS = (
    "helmet",
    "breastplate",
    "pants",
    "boots",
    "ring",
    "necklace",
    "weapon",
)
DEFAULT_DURABILITY = 100


def _salvar_player(player):
    salvar_json(PLAYER_PATH, player)


def _garantir_equipados(player):
    if "equipped" not in player or not isinstance(player["equipped"], dict):
        player["equipped"] = {}

    modificado = False
    for slot in EQUIPMENT_SLOTS:
        if slot not in player["equipped"]:
            player["equipped"][slot] = None
            modificado = True

    return modificado


def _garantir_durabilidade(item):
    modificado = False

    if "max_durability" not in item:
        item["max_durability"] = item.get("durability", DEFAULT_DURABILITY)
        modificado = True

    if "durability" not in item:
        item["durability"] = item["max_durability"]
        modificado = True

    return modificado


def calcular_atributos_totais(player):
    atributos_totais = player.get("attributes", {}).copy()

    if _garantir_equipados(player):
        _salvar_player(player)

    for item_equipado in player["equipped"].values():
        if not item_equipado:
            continue

        for attr, val in item_equipado.get("modifiers", {}).items():
            if attr in atributos_totais:
                atributos_totais[attr] += val
            else:
                atributos_totais[attr] = val

    return atributos_totais


def equipar_item(player, item):
    if not item:
        return False

    slot = item.get("slot")
    if slot not in EQUIPMENT_SLOTS:
        return False

    _garantir_equipados(player)
    _garantir_durabilidade(item)

    player["equipped"][slot] = item
    _salvar_player(player)
    return True


def reduzir_durabilidade(player, slot, quantidade=1):
    if slot not in EQUIPMENT_SLOTS:
        return {"quebrou": False}

    equipados_modificados = _garantir_equipados(player)
    item = player["equipped"].get(slot)
    if not item:
        if equipados_modificados:
            _salvar_player(player)
        return {"quebrou": False}

    _garantir_durabilidade(item)
    item["durability"] = max(0, item["durability"] - quantidade)

    if item["durability"] <= 0:
        nome_item = item.get("name", "Item desconhecido")
        player["equipped"][slot] = None
        _salvar_player(player)
        return {"quebrou": True, "nome_item": nome_item}

    _salvar_player(player)
    return {"quebrou": False}


def aplicar_desgaste_combate(player):
    avisos = []

    for slot in ("weapon", "breastplate"):
        quantidade = random.randint(1, 3)
        resultado = reduzir_durabilidade(player, slot, quantidade)

        if resultado.get("quebrou"):
            avisos.append(resultado)

    return avisos


def consumir_pocao(player, item):
    if not item or item.get("slot") != "potion":
        return []

    efeitos_aplicados = []
    modifiers = item.get("modifiers", {})

    for attr, val in modifiers.items():
        if attr == "hp_restore":
            max_hp = player.get("max_hp", 100)
            hp_atual = player.get("current_hp", max_hp)
            novo_hp = min(max_hp, hp_atual + val)
            player["current_hp"] = novo_hp
            efeitos_aplicados.append(("hp_restore", novo_hp - hp_atual))
            continue

        if attr in player.get("attributes", {}):
            player["attributes"][attr] += val
            efeitos_aplicados.append((attr, val))
        else:
            player[attr] = player.get(attr, 0) + val
            efeitos_aplicados.append((attr, val))

    if item in player.get("inventory", []):
        player["inventory"].remove(item)

    _salvar_player(player)
    return efeitos_aplicados
