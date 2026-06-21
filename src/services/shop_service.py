import math

from src.services.attribute_service import calcular_modificador_atributo
from src.services.combat_service import obter_efeitos_raciais
from src.services.database import carregar_json, salvar_json
from src.services.item_service import (
    adicionar_item_ao_inventario,
    calcular_atributos_totais,
    consolidar_itens_empilhaveis,
    obter_quantidade_item,
    remover_item_do_inventario,
)


PLAYER_PATH = "data/core/player.json"
ITEM_DATABASE_PATHS = (
    "data/items/oakridge/oakridge_store.json",
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
    "shield",
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


def _slots_da_loja(itens_disponiveis):
    return {
        item.get("slot")
        for item in (itens_disponiveis or {}).values()
        if item.get("slot")
    }


def jogador_tem_item_raro_da_loja(player, itens_disponiveis):
    slots_loja = _slots_da_loja(itens_disponiveis)
    if not slots_loja:
        return jogador_tem_item_raro(player)

    return any(
        item.get("slot") in slots_loja and item.get("rarity") in RARE_RARITIES
        for item in player.get("inventory", [])
    )


def jogador_tem_itens_no_inventario(player):
    return len(player.get("inventory", [])) > 0


def obter_memoria_loja(player, local_id, loja_id):
    memoria_geral = player.setdefault("shop_memory", {})
    if not isinstance(memoria_geral, dict):
        player["shop_memory"] = {}
        memoria_geral = player["shop_memory"]

    memoria_local = memoria_geral.setdefault(local_id, {})
    if not isinstance(memoria_local, dict):
        memoria_geral[local_id] = {}
        memoria_local = memoria_geral[local_id]

    return memoria_local.setdefault(loja_id, {"visits": 0, "purchases": 0})


def registrar_visita_loja(player, local_id, loja_id):
    memoria = obter_memoria_loja(player, local_id, loja_id)
    memoria["visits"] = int(memoria.get("visits", 0)) + 1
    salvar_json(PLAYER_PATH, player)
    return memoria


def registrar_compra_loja(player, local_id, loja_id):
    memoria = obter_memoria_loja(player, local_id, loja_id)
    memoria["purchases"] = int(memoria.get("purchases", 0)) + 1
    salvar_json(PLAYER_PATH, player)
    return memoria


def _montar_item_para_inventario(item_key, item_dados):
    item = {
        "id": item_key,
        "name": item_dados["name"],
        "price": item_dados.get("price", 0),
        "slot": item_dados["slot"],
        "modifiers": item_dados.get("modifiers", {}),
    }

    if "properties" in item_dados:
        item["properties"] = item_dados["properties"]

    if "description" in item_dados:
        item["description"] = item_dados["description"]

    if "restore" in item_dados:
        item["restore"] = item_dados["restore"]

    if "sell_price" in item_dados:
        item["sell_price"] = item_dados["sell_price"]

    if "stackable" in item_dados:
        item["stackable"] = item_dados["stackable"]

    if "rarity" in item_dados:
        item["rarity"] = item_dados["rarity"]

    if "level_required" in item_dados:
        item["level_required"] = item_dados["level_required"]

    if "grade" in item_dados:
        item["grade"] = item_dados["grade"]

    if "max_grade" in item_dados:
        item["max_grade"] = item_dados["max_grade"]

    if item["slot"] in EQUIPMENT_SLOTS:
        item["durability"] = item_dados.get("durability", DEFAULT_DURABILITY)
        item["max_durability"] = item_dados.get("max_durability", DEFAULT_DURABILITY)
        item.setdefault("grade", 0)
        item.setdefault("max_grade", item_dados.get("max_grade", 0))

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

    sell_price = item.get("sell_price")
    if sell_price is not None:
        return max(0, int(sell_price))

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
    consolidar_itens_empilhaveis(player)
    return [
        item for item in player.get("inventory", [])
        if not item_esta_equipado(player, item)
    ]


def vender_item(player, item, quantidade=1):
    if not item or item not in player.get("inventory", []):
        return {"sucesso": False, "valor": 0}

    quantidade_possuida = obter_quantidade_item(item)
    try:
        quantidade = max(1, int(quantidade))
    except (TypeError, ValueError):
        quantidade = 1

    if quantidade > quantidade_possuida:
        return {"sucesso": False, "valor": 0, "mensagem": "Quantidade insuficiente."}

    valor_unitario = calcular_valor_venda(item)
    valor = valor_unitario * quantidade
    remover_item_do_inventario(player, item, quantidade)
    player["gold"] = player.get("gold", 0) + valor
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True, "valor": valor, "quantidade": quantidade, "valor_unitario": valor_unitario}


def tentar_comprar_item(player, item_key, item_dados):
    preco = calcular_preco_final(player, item_dados)

    if player.get("gold", 0) < preco:
        return False

    player["gold"] -= preco

    if "inventory" not in player or not isinstance(player["inventory"], list):
        player["inventory"] = []

    consolidar_itens_empilhaveis(player, salvar=False)
    adicionar_item_ao_inventario(player, _montar_item_para_inventario(item_key, item_dados))

    return True
