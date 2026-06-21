from src.services.database import carregar_json, salvar_json
from src.services.item_service import (
    adicionar_item_ao_inventario,
    obter_grau_item,
    obter_grau_maximo_item,
    obter_quantidade_item,
    remover_item_do_inventario,
)


PLAYER_PATH = "data/core/player.json"
RECIPES_PATH = "data/core/equipment_upgrades.json"
GRADE_COSTS_PATH = "data/core/equipment_grade_costs.json"
ITEM_DATABASE_PATHS = (
    "data/items/oakridge/oakridge_store.json",
    "data/items/weapons/weapons_phandalin.json",
    "data/items/armor/armor_phandalin.json",
    "data/items/accessories/accessories_phandalin.json",
    "data/items/potions/potions_phandalin.json",
    "data/items/loot/materials.json",
    "data/items/loot/valuables.json",
    "data/items/loot/quest_items.json",
    "data/items/loot/special.json",
)
DEFAULT_DURABILITY = 100
EQUIPMENT_SLOTS = {
    "helmet",
    "breastplate",
    "pants",
    "boots",
    "shield",
    "ring",
    "necklace",
    "weapon",
}


def carregar_receitas_melhoria(village_id="phandalin", station_id="forge"):
    receitas = carregar_json(RECIPES_PATH) or {}
    receitas_vila = receitas.get(village_id, {}).get(station_id)
    if receitas_vila:
        return receitas_vila
    return receitas.get("phandalin", {}).get(station_id, {})


def carregar_custos_grau():
    return carregar_json(GRADE_COSTS_PATH) or {}


def carregar_banco_itens():
    banco = {}
    for caminho in ITEM_DATABASE_PATHS:
        dados = carregar_json(caminho) or {}
        banco.update(dados)
    return banco


def obter_item_banco(item_id):
    return carregar_banco_itens().get(item_id)


def montar_item_para_inventario(item_id):
    dados = obter_item_banco(item_id)
    if not dados:
        return None

    item = {
        "id": item_id,
        "name": dados.get("name", item_id),
        "price": dados.get("price", 0),
        "slot": dados.get("slot"),
        "modifiers": dados.get("modifiers", {}),
    }

    for chave in (
        "description",
        "restore",
        "remove_condition",
        "applies_condition",
        "properties",
        "sell_price",
        "stackable",
        "rarity",
        "level_required",
        "category",
        "grade",
        "max_grade",
    ):
        if chave in dados:
            item[chave] = dados[chave]

    if item.get("slot") in EQUIPMENT_SLOTS:
        item["durability"] = dados.get("durability", DEFAULT_DURABILITY)
        item["max_durability"] = dados.get("max_durability", DEFAULT_DURABILITY)
        item.setdefault("grade", 0)
        item.setdefault("max_grade", dados.get("max_grade", 0))

    return item


def _obter_item_inventario(player, item_id):
    for item in player.get("inventory", []):
        if item.get("id") == item_id:
            return item
    return None


def _obter_item_equipado(player, item_id):
    for slot, item in player.get("equipped", {}).items():
        if item and item.get("id") == item_id:
            return slot, item
    return None, None


def _itens_equipamento_do_player(player):
    for slot, item in player.get("equipped", {}).items():
        if item and item.get("slot") in EQUIPMENT_SLOTS:
            yield {"origin": "equipped", "slot": slot, "item": item}

    for item in player.get("inventory", []):
        if item.get("slot") in EQUIPMENT_SLOTS:
            yield {"origin": "inventory", "slot": None, "item": item}


def _sincronizar_max_grade_do_banco(item):
    if not item or obter_grau_maximo_item(item) > 0:
        item.setdefault("grade", obter_grau_item(item))
        return

    dados_banco = obter_item_banco(item.get("id"))
    if dados_banco and int(dados_banco.get("max_grade", 0)) > 0:
        item["max_grade"] = int(dados_banco.get("max_grade", 0))
    item.setdefault("grade", obter_grau_item(item))


def listar_itens_aprimoraveis_grau(player):
    itens = []
    for entrada in _itens_equipamento_do_player(player):
        item = entrada["item"]
        _sincronizar_max_grade_do_banco(item)
        grau = obter_grau_item(item)
        grau_maximo = obter_grau_maximo_item(item)
        if grau_maximo <= 0 or grau >= grau_maximo:
            continue
        itens.append(entrada)
    return itens


def obter_custo_proximo_grau(item):
    proximo_grau = obter_grau_item(item) + 1
    return carregar_custos_grau().get(f"grade_{proximo_grau}")


def jogador_tem_item_base(player, item_id):
    if _obter_item_inventario(player, item_id):
        return True
    _, item = _obter_item_equipado(player, item_id)
    return item is not None


def quantidade_item(player, item_id):
    item = _obter_item_inventario(player, item_id)
    if not item:
        return 0
    return obter_quantidade_item(item)


def avaliar_receita(player, receita):
    materiais = receita.get("materials", {})
    requisitos_materiais = {
        item_id: {
            "required": quantidade,
            "current": quantidade_item(player, item_id),
            "ok": quantidade_item(player, item_id) >= quantidade,
        }
        for item_id, quantidade in materiais.items()
    }

    ouro_atual = int(player.get("gold", 0))
    custo_ouro = int(receita.get("gold_cost", 0))
    return {
        "base_ok": jogador_tem_item_base(player, receita.get("base_item")),
        "gold_ok": ouro_atual >= custo_ouro,
        "gold_current": ouro_atual,
        "gold_required": custo_ouro,
        "materials": requisitos_materiais,
    }


def avaliar_aprimoramento_grau(player, item):
    _sincronizar_max_grade_do_banco(item)
    grau = obter_grau_item(item)
    grau_maximo = obter_grau_maximo_item(item)
    if grau_maximo <= 0:
        return {"upgradeable": False, "mensagem": "Este item nao aceita graus."}
    if grau >= grau_maximo:
        return {"upgradeable": False, "mensagem": "Este item ja esta no grau maximo."}

    custo = obter_custo_proximo_grau(item)
    if not custo:
        return {"upgradeable": False, "mensagem": "Custo do proximo grau nao configurado."}

    materiais = custo.get("materials", {})
    requisitos_materiais = {
        item_id: {
            "required": quantidade,
            "current": quantidade_item(player, item_id),
            "ok": quantidade_item(player, item_id) >= quantidade,
        }
        for item_id, quantidade in materiais.items()
    }
    ouro_atual = int(player.get("gold", 0))
    custo_ouro = int(custo.get("gold_cost", 0))
    return {
        "upgradeable": True,
        "grade": grau,
        "next_grade": grau + 1,
        "max_grade": grau_maximo,
        "gold_ok": ouro_atual >= custo_ouro,
        "gold_current": ouro_atual,
        "gold_required": custo_ouro,
        "materials": requisitos_materiais,
    }


def aprimoramento_grau_disponivel(player, item):
    avaliacao = avaliar_aprimoramento_grau(player, item)
    return (
        avaliacao.get("upgradeable")
        and avaliacao.get("gold_ok")
        and all(material["ok"] for material in avaliacao.get("materials", {}).values())
    )


def receita_disponivel(player, receita):
    avaliacao = avaliar_receita(player, receita)
    return (
        avaliacao["base_ok"]
        and avaliacao["gold_ok"]
        and all(material["ok"] for material in avaliacao["materials"].values())
    )


def _remover_item_base(player, item_id):
    slot, item_equipado = _obter_item_equipado(player, item_id)
    if item_equipado:
        player["equipped"][slot] = None
        return item_equipado

    item_inventario = _obter_item_inventario(player, item_id)
    if item_inventario:
        remover_item_do_inventario(player, item_inventario, 1)
        return item_inventario

    return None


def melhorar_equipamento(player, recipe_id, village_id="phandalin", station_id="forge"):
    receitas = carregar_receitas_melhoria(village_id, station_id)
    receita = receitas.get(recipe_id)
    if not receita:
        return {"sucesso": False, "mensagem": "Receita nao encontrada."}

    avaliacao = avaliar_receita(player, receita)
    if not receita_disponivel(player, receita):
        return {
            "sucesso": False,
            "mensagem": "Faltam requisitos para essa melhoria.",
            "avaliacao": avaliacao,
        }

    item_resultado = montar_item_para_inventario(receita.get("result_item"))
    if not item_resultado:
        return {"sucesso": False, "mensagem": "Item resultado nao encontrado no banco de itens."}

    item_base = _remover_item_base(player, receita.get("base_item"))
    if not item_base:
        return {"sucesso": False, "mensagem": "Item base nao encontrado."}

    for item_id, quantidade in receita.get("materials", {}).items():
        item_material = _obter_item_inventario(player, item_id)
        if item_material:
            remover_item_do_inventario(player, item_material, quantidade)

    player["gold"] = max(0, int(player.get("gold", 0)) - int(receita.get("gold_cost", 0)))
    adicionar_item_ao_inventario(player, item_resultado)
    salvar_json(PLAYER_PATH, player)

    return {
        "sucesso": True,
        "receita": receita,
        "item_base": item_base,
        "item_resultado": item_resultado,
    }


def aprimorar_grau_item(player, item):
    if not item:
        return {"sucesso": False, "mensagem": "Item nao encontrado."}

    avaliacao = avaliar_aprimoramento_grau(player, item)
    if not avaliacao.get("upgradeable"):
        return {"sucesso": False, "mensagem": avaliacao.get("mensagem", "Item nao pode ser aprimorado.")}
    if not aprimoramento_grau_disponivel(player, item):
        return {
            "sucesso": False,
            "mensagem": "Faltam requisitos para aprimorar o grau.",
            "avaliacao": avaliacao,
        }

    custo = obter_custo_proximo_grau(item)
    for item_id, quantidade in custo.get("materials", {}).items():
        item_material = _obter_item_inventario(player, item_id)
        if item_material:
            remover_item_do_inventario(player, item_material, quantidade)

    player["gold"] = max(0, int(player.get("gold", 0)) - int(custo.get("gold_cost", 0)))
    item["grade"] = avaliacao["next_grade"]
    item.setdefault("max_grade", avaliacao["max_grade"])
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True, "item": item, "avaliacao": avaliacao}
