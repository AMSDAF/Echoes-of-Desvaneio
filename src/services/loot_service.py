from copy import deepcopy

from src.services.item_catalog_service import buscar_item_catalogo, carregar_catalogo_itens


def carregar_loot_database():
    return carregar_catalogo_itens()


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
    item = buscar_item_catalogo(item_id)
    if not item:
        return criar_loot_fallback(item_id)

    item = deepcopy(item)
    item["id"] = item_id
    return item


def montar_loot_para_inventario(item_id):
    item = buscar_loot_por_id(item_id)
    item["type"] = item.get("category", "material")
    return item
