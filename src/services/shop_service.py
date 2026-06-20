import math

from src.services.attribute_service import calcular_modificador_atributo
from src.services.combat_service import obter_efeitos_raciais
from src.services.database import carregar_json, salvar_json
from src.services.item_service import calcular_atributos_totais


PLAYER_PATH = "data/core/player.json"
ITEM_DATABASE_PATHS = (
    "data/items/weapons/weapons_phandalin.json",
    "data/items/armor/armor_phandalin.json",
    "data/items/accessories/accessories_phandalin.json",
    "data/items/potions/potions_phandalin.json",
)
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
MATERIAL_VALUES = {
    "couro_estragado": 2,
    "dente_afiado": 3,
    "farrapo_tecido": 3,
    "lasca_ferro": 5,
    "orelha_goblin": 8,
    "couro_grosso": 8,
    "soro_mutante": 14,
    "coroa_esgoto": 35,
    "cauda_real": 18,
    "moeda_velha": 6,
    "bandana_suja": 5,
    "po_osso": 5,
    "fragmento_escudo": 9,
    "essencia_magica": 18,
    "pergaminho_rasgado": 12,
    "pele_urso": 30,
    "fragmento_aco": 22,
    "chifre_bugbear": 28,
    "veneno_basico": 14,
    "geleia_acida": 12,
    "nucleo_elementar_fraco": 25,
    "escama_duravel": 22,
    "dente_jacare": 18,
    "tentaculo_preservado": 45,
    "cristal_psionico": 60,
}


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
        "price": item_dados.get("price", 0),
        "slot": item_dados["slot"],
        "modifiers": item_dados.get("modifiers", {}),
    }

    if "description" in item_dados:
        item["description"] = item_dados["description"]

    if "restore" in item_dados:
        item["restore"] = item_dados["restore"]

    if "rarity" in item_dados:
        item["rarity"] = item_dados["rarity"]

    if "level_required" in item_dados:
        item["level_required"] = item_dados["level_required"]

    if item["slot"] in EQUIPMENT_SLOTS:
        item["durability"] = item_dados.get("durability", DEFAULT_DURABILITY)
        item["max_durability"] = item_dados.get("max_durability", DEFAULT_DURABILITY)

    return item


def calcular_desconto_carisma(player):
    atributos = calcular_atributos_totais(player)
    mod_cha = calcular_modificador_atributo(atributos.get("charisma", 10))
    efeitos_raciais = obter_efeitos_raciais(player)

    desconto = max(0, mod_cha) * 0.02
    desconto += efeitos_raciais.get("charisma_check_bonus", 0)

    return min(0.25, max(0, desconto))


def calcular_preco_final(player, item_dados):
    preco_base = max(0, int(item_dados.get("price", 0)))
    desconto = calcular_desconto_carisma(player)
    return max(1, math.ceil(preco_base * (1 - desconto)))


def obter_preco_base_item(item):
    preco = int(item.get("price", 0))
    if preco > 0:
        return preco

    item_id = item.get("id")
    if not item_id:
        return 0

    for caminho in ITEM_DATABASE_PATHS:
        dados = carregar_json(caminho) or {}
        if item_id in dados:
            return int(dados[item_id].get("price", 0))

    return 0


def item_esta_equipado(player, item):
    return any(item == equipado for equipado in player.get("equipped", {}).values() if equipado)


def calcular_valor_venda(item):
    if not item:
        return 0

    if item.get("type") == "material":
        return MATERIAL_VALUES.get(item.get("id"), 3)

    preco_base = obter_preco_base_item(item)
    if preco_base <= 0:
        return 2

    slot = item.get("slot")
    if slot == "consumable":
        return max(1, math.floor(preco_base * 0.35))

    durabilidade = item.get("current_durability", item.get("durability", item.get("max_durability", 100)))
    durabilidade_maxima = item.get("max_durability", 100)
    fator_durabilidade = 1 if durabilidade_maxima <= 0 else max(0.15, durabilidade / durabilidade_maxima)
    return max(1, math.floor(preco_base * 0.50 * fator_durabilidade))


def listar_itens_vendiveis(player):
    return [
        item for item in player.get("inventory", [])
        if not item_esta_equipado(player, item)
    ]


def vender_item(player, item):
    if not item or item not in player.get("inventory", []):
        return {"sucesso": False, "valor": 0}

    valor = calcular_valor_venda(item)
    player["inventory"].remove(item)
    player["gold"] = player.get("gold", 0) + valor
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True, "valor": valor}


def tentar_comprar_item(player, item_key, item_dados):
    if player.get("level", 1) < item_dados.get("level_required", 1):
        return False

    preco = calcular_preco_final(player, item_dados)

    if player.get("gold", 0) < preco:
        return False

    player["gold"] -= preco

    if "inventory" not in player or not isinstance(player["inventory"], list):
        player["inventory"] = []

    player["inventory"].append(_montar_item_para_inventario(item_key, item_dados))
    salvar_json(PLAYER_PATH, player)

    return True
