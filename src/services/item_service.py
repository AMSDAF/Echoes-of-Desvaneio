import random

from src.services.attribute_service import (
    ATRIBUTOS_LEGADOS,
    calcular_modificador_atributo,
    normalizar_atributos,
)
from src.services.condition_service import (
    adicionar_condicao,
    calcular_multiplicador_desgaste,
    obter_nome_condicao,
    remove_condicao,
)
from src.services.database import salvar_json


PLAYER_PATH = "data/core/player.json"
EQUIPMENT_SLOTS = (
    "helmet",
    "breastplate",
    "pants",
    "boots",
    "shield",
    "ring",
    "necklace",
    "weapon",
)
DEFAULT_DURABILITY = 100
PROPRIEDADES_NUMERICAS = (
    "damage_bonus",
    "physical_damage_bonus",
    "magic_damage_bonus",
    "crit_chance_bonus",
    "crit_damage_multiplier_bonus",
    "physical_damage_reduction",
    "magic_damage_reduction",
    "durability_loss_reduction",
    "healing_bonus",
    "escape_bonus",
    "gold_bonus",
    "xp_bonus",
    "defense_bonus",
)
NUMERAIS_GRAU = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
}


def _salvar_player(player):
    salvar_json(PLAYER_PATH, player)


def obter_quantidade_item(item):
    try:
        return max(1, int((item or {}).get("quantity", 1)))
    except (TypeError, ValueError):
        return 1


def item_e_empilhavel(item):
    if not item:
        return False

    if item.get("stackable") is False:
        return False

    return item.get("stackable") is True or item.get("slot") in {"consumable", "potion"}


def formatar_nome_com_quantidade(item):
    nome = formatar_nome_com_grau(item)
    quantidade = obter_quantidade_item(item)
    if quantidade > 1:
        return f"{nome} x{quantidade}"
    return nome


def obter_grau_item(item):
    try:
        return max(0, int((item or {}).get("grade", 0)))
    except (TypeError, ValueError):
        return 0


def obter_grau_maximo_item(item):
    try:
        return max(0, int((item or {}).get("max_grade", 0)))
    except (TypeError, ValueError):
        return 0


def formatar_nome_com_grau(item):
    nome = (item or {}).get("name", "Item desconhecido")
    grau = obter_grau_item(item)
    if grau <= 0:
        return nome
    return f"{nome} [Grau {NUMERAIS_GRAU.get(grau, grau)}]"


def consolidar_itens_empilhaveis(player, salvar=True):
    """Agrupa duplicatas empilhaveis sem tocar em equipamentos ou itens unicos."""
    inventario = player.get("inventory")
    if not isinstance(inventario, list):
        player["inventory"] = []
        if salvar:
            _salvar_player(player)
        return True

    grupos = {}
    novo_inventario = []
    modificado = False

    for item in inventario:
        if not item_e_empilhavel(item) or not item.get("id"):
            novo_inventario.append(item)
            continue

        item_id = item["id"]
        quantidade = obter_quantidade_item(item)
        if item_id in grupos:
            grupos[item_id]["quantity"] = obter_quantidade_item(grupos[item_id]) + quantidade
            modificado = True
            continue

        if item.get("quantity") != quantidade:
            item["quantity"] = quantidade
            modificado = True

        grupos[item_id] = item
        novo_inventario.append(item)

    if modificado:
        player["inventory"] = novo_inventario
        if salvar:
            _salvar_player(player)

    return modificado


def adicionar_item_ao_inventario(player, item, quantidade=1):
    if not item:
        return None

    if "inventory" not in player or not isinstance(player["inventory"], list):
        player["inventory"] = []

    try:
        quantidade = max(1, int(quantidade))
    except (TypeError, ValueError):
        quantidade = 1

    item_id = item.get("id")
    if item_e_empilhavel(item) and item_id:
        consolidar_itens_empilhaveis(player, salvar=False)
        for item_existente in player["inventory"]:
            if item_e_empilhavel(item_existente) and item_existente.get("id") == item_id:
                item_existente["quantity"] = obter_quantidade_item(item_existente) + quantidade
                for chave, valor in item.items():
                    if chave != "quantity" and chave not in item_existente:
                        item_existente[chave] = valor
                _salvar_player(player)
                return item_existente

    novo_item = dict(item)
    novo_item["quantity"] = quantidade
    player["inventory"].append(novo_item)
    _salvar_player(player)
    return novo_item


def remover_item_do_inventario(player, item, quantidade=1):
    if not item or item not in player.get("inventory", []):
        return False

    try:
        quantidade = max(1, int(quantidade))
    except (TypeError, ValueError):
        quantidade = 1

    quantidade_atual = obter_quantidade_item(item)
    if quantidade_atual > quantidade:
        item["quantity"] = quantidade_atual - quantidade
    else:
        player["inventory"].remove(item)

    _salvar_player(player)
    return True


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
        item["max_durability"] = item.get("durability", item.get("current_durability", DEFAULT_DURABILITY))
        modificado = True

    if "durability" not in item:
        item["durability"] = item.get("current_durability", item["max_durability"])
        modificado = True

    item["current_durability"] = item["durability"]
    return modificado


def obter_razao_durabilidade(item):
    if not item:
        return 1

    max_durability = item.get("max_durability", item.get("durability", DEFAULT_DURABILITY))
    current_durability = item.get("current_durability", item.get("durability", max_durability))
    if max_durability <= 0:
        return 1

    return current_durability / max_durability


def calcular_atributos_totais(player):
    atributos_normalizados = normalizar_atributos(player.get("attributes", {}))
    if player.get("attributes") != atributos_normalizados:
        player["attributes"] = atributos_normalizados
        _salvar_player(player)

    atributos_totais = atributos_normalizados.copy()

    if _garantir_equipados(player):
        _salvar_player(player)

    for item_equipado in player["equipped"].values():
        if not item_equipado:
            continue

        for attr, val in item_equipado.get("modifiers", {}).items():
            attr_normalizado = ATRIBUTOS_LEGADOS.get(attr, attr)
            if attr_normalizado in atributos_totais:
                atributos_totais[attr_normalizado] += val
            else:
                atributos_totais[attr_normalizado] = val

    return atributos_totais


def _somar_propriedade_numerica(destino, chave, valor):
    try:
        destino[chave] = destino.get(chave, 0) + float(valor)
    except (TypeError, ValueError):
        return


def calcular_propriedades_equipadas(player):
    if _garantir_equipados(player):
        _salvar_player(player)

    propriedades = {
        "condition_resistance": {},
        "resource_cost_reduction": {},
        "on_hit_conditions": [],
        "has_shield": False,
    }

    for item_equipado in player.get("equipped", {}).values():
        if not item_equipado:
            continue

        if item_equipado.get("slot") == "shield":
            propriedades["has_shield"] = True

        item_properties = item_equipado.get("properties", {})
        for chave in PROPRIEDADES_NUMERICAS:
            if chave in item_properties:
                _somar_propriedade_numerica(propriedades, chave, item_properties[chave])

        for condicao, bonus in item_properties.get("condition_resistance", {}).items():
            _somar_propriedade_numerica(propriedades["condition_resistance"], condicao, bonus)

        for recurso, reducao in item_properties.get("resource_cost_reduction", {}).items():
            _somar_propriedade_numerica(propriedades["resource_cost_reduction"], recurso, reducao)

        on_hit = item_properties.get("on_hit_condition")
        if on_hit:
            propriedades["on_hit_conditions"].append(on_hit)

        grau = obter_grau_item(item_equipado)
        if grau > 0:
            if item_equipado.get("slot") == "weapon":
                _somar_propriedade_numerica(propriedades, "physical_damage_bonus", grau)
            elif item_equipado.get("slot") in {"helmet", "breastplate", "pants", "boots", "shield"}:
                _somar_propriedade_numerica(propriedades, "defense_bonus", grau)

    return propriedades


def obter_bonus_resistencia_condicao(player, condition_id):
    propriedades = calcular_propriedades_equipadas(player)
    return int(propriedades.get("condition_resistance", {}).get(condition_id, 0))


def obter_condicoes_ao_acertar(player):
    return calcular_propriedades_equipadas(player).get("on_hit_conditions", [])


def calcular_reducao_desgaste_equipamento(player):
    propriedades = calcular_propriedades_equipadas(player)
    return min(0.75, max(0, propriedades.get("durability_loss_reduction", 0)))


def formatar_propriedades_item(item):
    properties = item.get("properties", {})
    if not properties:
        return []

    descricoes = []

    textos_numericos = {
        "damage_bonus": "Dano +{}",
        "physical_damage_bonus": "Dano fisico +{}",
        "magic_damage_bonus": "Dano magico +{}",
        "crit_chance_bonus": "Critico +{}%",
        "crit_damage_multiplier_bonus": "Dano critico +{}%",
        "physical_damage_reduction": "Reducao fisica {}%",
        "magic_damage_reduction": "Reducao magica {}%",
        "durability_loss_reduction": "Desgaste -{}%",
        "healing_bonus": "Cura +{}%",
        "escape_bonus": "Fuga +{}%",
        "gold_bonus": "Ouro +{}%",
        "xp_bonus": "XP +{}%",
        "defense_bonus": "Defesa +{}",
    }

    for chave, modelo in textos_numericos.items():
        if chave not in properties:
            continue

        valor = properties[chave]
        if isinstance(valor, float) and abs(valor) < 1:
            valor = int(round(valor * 100))
        descricoes.append(modelo.format(valor))

    if properties.get("resource_cost_reduction"):
        nomes = {"mana": "Mana", "stamina": "Estamina"}
        for recurso, reducao in properties["resource_cost_reduction"].items():
            descricoes.append(f"Custo de {nomes.get(recurso, recurso)} -{int(round(reducao * 100))}%")

    if properties.get("condition_resistance"):
        for condition_id, bonus in properties["condition_resistance"].items():
            descricoes.append(f"+{bonus} em testes contra {obter_nome_condicao(condition_id)}")

    if properties.get("on_hit_condition"):
        condicao = properties["on_hit_condition"]
        chance = int(round(float(condicao.get("chance", 1)) * 100))
        descricoes.append(f"{chance}% de aplicar {obter_nome_condicao(condicao.get('id'))} ao acertar")

    return descricoes


def equipar_item(player, item):
    if not item:
        return False

    slot = item.get("slot")
    if slot not in EQUIPMENT_SLOTS:
        return False

    if player.get("level", 1) < item.get("level_required", 1):
        return False

    _garantir_equipados(player)
    _garantir_durabilidade(item)

    item_antigo = player["equipped"].get(slot)
    if item in player.get("inventory", []):
        player["inventory"].remove(item)

    if item_antigo:
        player.setdefault("inventory", []).append(item_antigo)

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
    reducao_desgaste = calcular_reducao_desgaste_equipamento(player)
    quantidade_final = max(1, int(round(quantidade * (1 - reducao_desgaste))))
    item["durability"] = max(0, item["durability"] - quantidade_final)
    item["current_durability"] = item["durability"]

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


def aplicar_desgaste_defensivo(player, postura_defesa, dano_recebido):
    if dano_recebido <= 0:
        return []

    desgaste_por_postura = {
        "bloquear": (2, 4),
        "sem_defesa": (2, 3),
        "contra_atacar": (1, 3),
        "esquivar": (1, 2),
    }
    minimo, maximo = desgaste_por_postura.get(postura_defesa, (1, 2))
    multiplicador_desgaste = calcular_multiplicador_desgaste(player)

    slots_alvo = ("breastplate", "shield", "helmet", "pants", "boots")
    slots_equipados = [
        slot for slot in slots_alvo
        if player.get("equipped", {}).get(slot)
    ]

    if not slots_equipados:
        return []

    avisos = []
    slot_principal = "breastplate" if "breastplate" in slots_equipados else random.choice(slots_equipados)
    resultado = reduzir_durabilidade(player, slot_principal, random.randint(minimo, maximo) * multiplicador_desgaste)
    if resultado.get("quebrou"):
        avisos.append(resultado)

    if postura_defesa == "bloquear" and len(slots_equipados) > 1 and random.random() <= 0.35:
        slots_secundarios = [slot for slot in slots_equipados if slot != slot_principal]
        resultado = reduzir_durabilidade(player, random.choice(slots_secundarios), 1 * multiplicador_desgaste)
        if resultado.get("quebrou"):
            avisos.append(resultado)

    return avisos


def calcular_multiplicador_cura(player):
    atributos = calcular_atributos_totais(player)
    mod_wis = calcular_modificador_atributo(atributos.get("wisdom", 10))
    propriedades = calcular_propriedades_equipadas(player)
    bonus_item = min(0.50, max(0, propriedades.get("healing_bonus", 0)))
    return 1 + min(0.40, max(0, mod_wis) * 0.05) + bonus_item


def item_e_consumivel(item):
    return bool(item) and item.get("slot") in {"consumable", "potion"}


def _obter_restauro_consumivel(item):
    restore = item.get("restore")
    if restore:
        return restore.get("resource"), int(restore.get("value", 0))

    modifiers = item.get("modifiers", {})
    if "hp_restore" in modifiers:
        return "hp", int(modifiers.get("hp_restore", 0))

    return None, 0


def _nome_recurso_restaurado(resource):
    nomes = {
        "hp": "Vida",
        "mana": "Mana",
        "stamina": "Estamina",
    }
    return nomes.get(resource, resource or "recurso")


def consumir_consumivel(player, item):
    if not item_e_consumivel(item):
        return {"sucesso": False, "mensagem": "Item invalido."}

    resource, value = _obter_restauro_consumivel(item)
    remove_condition = item.get("remove_condition")
    applies_condition = item.get("applies_condition")

    if resource not in {"hp", "mana", "stamina"} or value <= 0:
        if remove_condition:
            removido = remove_condicao(player, remove_condition)
            if not removido:
                return {
                    "sucesso": False,
                    "mensagem": f"Voce nao esta sob efeito de {obter_nome_condicao(remove_condition)}.",
                }

            remover_item_do_inventario(player, item)
            return {
                "sucesso": True,
                "item_name": item.get("name", "Consumivel"),
                "condition_removed": remove_condition,
                "condition_name": obter_nome_condicao(remove_condition),
            }

        if applies_condition:
            condicao = adicionar_condicao(player, applies_condition)
            if not condicao:
                return {"sucesso": False, "mensagem": "Esse item nao pode ser usado agora."}

            remover_item_do_inventario(player, item)
            return {
                "sucesso": True,
                "item_name": item.get("name", "Consumivel"),
                "condition_applied": condicao.get("id"),
                "condition_name": condicao.get("name", obter_nome_condicao(condicao.get("id"))),
                "duration": condicao.get("duration", 1),
            }

        return {"sucesso": False, "mensagem": "Esse item nao pode ser usado em combate."}

    current_key = f"current_{resource}"
    max_key = f"max_{resource}"
    max_value = player.get(max_key, 100 if resource == "hp" else 50)
    current_value = player.get(current_key, max_value)
    restore_value = int(round(value * calcular_multiplicador_cura(player)))
    new_value = min(max_value, current_value + restore_value)
    restored = new_value - current_value

    player[current_key] = new_value

    remover_item_do_inventario(player, item)
    return {
        "sucesso": True,
        "item_name": item.get("name", "Consumivel"),
        "resource": resource,
        "resource_name": _nome_recurso_restaurado(resource),
        "restored": restored,
    }


def consumir_pocao(player, item):
    if not item_e_consumivel(item):
        return []

    if (
        item.get("restore")
        or "hp_restore" in item.get("modifiers", {})
        or item.get("remove_condition")
        or item.get("applies_condition")
    ):
        resultado = consumir_consumivel(player, item)
        if not resultado.get("sucesso"):
            return []

        if "resource" in resultado:
            return [(f"{resultado['resource']}_restore", resultado["restored"])]

        if "condition_removed" in resultado:
            return [("condition_removed", resultado["condition_name"])]

        if "condition_applied" in resultado:
            return [("condition_applied", resultado["condition_name"])]

        return []

    efeitos_aplicados = []
    modifiers = item.get("modifiers", {})

    for attr, val in modifiers.items():
        if attr == "hp_restore":
            max_hp = player.get("max_hp", 100)
            hp_atual = player.get("current_hp", max_hp)
            cura_total = int(round(val * calcular_multiplicador_cura(player)))
            novo_hp = min(max_hp, hp_atual + cura_total)
            player["current_hp"] = novo_hp
            efeitos_aplicados.append(("hp_restore", novo_hp - hp_atual))
            continue

        attr_normalizado = ATRIBUTOS_LEGADOS.get(attr, attr)
        player["attributes"] = normalizar_atributos(player.get("attributes", {}))

        if attr_normalizado in player.get("attributes", {}):
            player["attributes"][attr_normalizado] += val
            efeitos_aplicados.append((attr_normalizado, val))
        else:
            player[attr_normalizado] = player.get(attr_normalizado, 0) + val
            efeitos_aplicados.append((attr_normalizado, val))

    remover_item_do_inventario(player, item)
    return efeitos_aplicados
