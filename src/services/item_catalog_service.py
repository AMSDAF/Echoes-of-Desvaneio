from functools import lru_cache
from pathlib import Path

from src.services.database import carregar_json


ITEM_CATALOG_ROOTS = (
    Path("data/items/equipment/weapons"),
    Path("data/items/equipment/shields"),
    Path("data/items/equipment/armor"),
    Path("data/items/equipment/accessories"),
    Path("data/items/equipment/potions"),
    Path("data/items/materials"),
    Path("data/items/valuables"),
    Path("data/items/special"),
    Path("data/items/quest_items"),
)
SHIELD_IDENTIFIERS = {"shield", "shields", "escudo", "escudos"}


def normalizar_slot_item(item):
    if not isinstance(item, dict):
        return None

    slot = str(item.get("slot", "")).strip().lower()
    categoria = str(item.get("category", "")).strip().lower()
    tipo = str(item.get("type", "")).strip().lower()
    if slot in SHIELD_IDENTIFIERS or categoria in SHIELD_IDENTIFIERS or tipo in SHIELD_IDENTIFIERS:
        return "shield"

    return slot or None


@lru_cache(maxsize=1)
def carregar_catalogo_itens():
    catalogo = {}
    for pasta in ITEM_CATALOG_ROOTS:
        if not pasta.exists():
            continue

        for caminho in sorted(pasta.rglob("*.json")):
            dados = carregar_json(str(caminho)) or {}
            if not isinstance(dados, dict):
                continue

            for item_id, item in dados.items():
                if isinstance(item, dict):
                    item_catalogado = dict(item)
                    slot = normalizar_slot_item(item_catalogado)
                    if slot:
                        item_catalogado["slot"] = slot
                    catalogo[item_id] = item_catalogado

    return catalogo


def buscar_item_catalogo(item_id):
    return carregar_catalogo_itens().get(item_id)


def resolver_inventory_loja(inventory):
    catalogo = carregar_catalogo_itens()
    itens = {}
    ausentes = []

    if not isinstance(inventory, dict):
        return itens, ausentes

    for item_ids in inventory.values():
        if not isinstance(item_ids, list):
            continue

        for item_id in item_ids:
            item = catalogo.get(item_id)
            if item is None:
                ausentes.append(item_id)
                continue
            itens[item_id] = item

    return itens, ausentes
