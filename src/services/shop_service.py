from src.services.database import salvar_json


PLAYER_PATH = "data/core/player.json"
DEFAULT_DURABILITY = 100
EQUIPMENT_SLOTS = {
    "helmet",
    "breastplate",
    "pants",
    "boots",
    "ring",
    "necklace",
    "weapon",
}
RARE_RARITIES = {"raro", "epico", "lendario"}


def jogador_tem_item_raro(player):
    return any(
        item.get("rarity") in RARE_RARITIES
        for item in player.get("inventory", [])
    )


def jogador_tem_itens_no_inventario(player):
    return len(player.get("inventory", [])) > 0


def _montar_item_para_inventario(item_key, item_dados):
    item = {
        "id": item_key,
        "name": item_dados["name"],
        "slot": item_dados["slot"],
        "modifiers": item_dados.get("modifiers", {}),
    }

    if "rarity" in item_dados:
        item["rarity"] = item_dados["rarity"]

    if item["slot"] in EQUIPMENT_SLOTS:
        item["durability"] = item_dados.get("durability", DEFAULT_DURABILITY)
        item["max_durability"] = item_dados.get("max_durability", DEFAULT_DURABILITY)

    return item


def tentar_comprar_item(player, item_key, item_dados):
    preco = item_dados.get("price", 0)

    if player.get("gold", 0) < preco:
        return False

    player["gold"] -= preco

    if "inventory" not in player or not isinstance(player["inventory"], list):
        player["inventory"] = []

    player["inventory"].append(_montar_item_para_inventario(item_key, item_dados))
    salvar_json(PLAYER_PATH, player)

    return True
