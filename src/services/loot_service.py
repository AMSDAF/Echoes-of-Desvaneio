from copy import deepcopy

from src.services.database import carregar_json


LOOT_DATABASE_PATHS = (
    "data/items/loot/materials.json",
    "data/items/loot/valuables.json",
    "data/items/loot/quest_items.json",
    "data/items/loot/special.json",
)


def carregar_loot_database():
    loot_database = {}
    for caminho in LOOT_DATABASE_PATHS:
        dados = carregar_json(caminho) or {}
        loot_database.update(dados)
    return loot_database


def criar_loot_fallback(item_id):
    nome = str(item_id or "item_desconhecido").replace("_", " ").title()
    return {
        "id": item_id,
        "name": nome,
        "description": "Item encontrado, mas ainda sem cadastro detalhado.",
        "rarity": "common",
        "category": "material",
        "sell_price": 0,
        "stackable": True,
        "crafting": {
            "usable": False,
            "tags": ["uncatalogued"],
        },
    }


def buscar_loot_por_id(item_id):
    loot_database = carregar_loot_database()
    item = loot_database.get(item_id)
    if not item:
        return criar_loot_fallback(item_id)

    item = deepcopy(item)
    item["id"] = item_id
    return item


def montar_loot_para_inventario(item_id):
    item = buscar_loot_por_id(item_id)
    item["type"] = item.get("category", "material")
    return item
