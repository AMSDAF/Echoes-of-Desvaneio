import random

from src.services.attribute_service import calcular_modificador_atributo, normalizar_atributos
from src.services.database import carregar_json, salvar_json
from src.services.dice_service import rolar_d20_interativo


PLAYER_PATH = "data/core/player.json"
EVENTS_PATH = "data/core/exploration_events.json"
TOWN_EVENTS_PATH = "data/core/town_events.json"


def carregar_eventos_exploracao():
    return carregar_json(EVENTS_PATH) or {}


def carregar_eventos_urbanos():
    return carregar_json(TOWN_EVENTS_PATH) or {}


def listar_eventos_area(village_id, area_id):
    return carregar_eventos_exploracao().get(village_id, {}).get(area_id, [])


def sortear_evento_exploracao(village_id, area_id):
    eventos = listar_eventos_area(village_id, area_id)
    if not eventos:
        return None

    pesos = [max(1, int(evento.get("weight", 1))) for evento in eventos]
    return random.choices(eventos, weights=pesos)[0]


def listar_eventos_urbanos(village_id, contexto):
    return carregar_eventos_urbanos().get(village_id, {}).get(contexto, [])


def sortear_evento_urbano(village_id, contexto):
    eventos = listar_eventos_urbanos(village_id, contexto)
    if not eventos:
        return None

    pesos = [max(1, int(evento.get("weight", 1))) for evento in eventos]
    return random.choices(eventos, weights=pesos)[0]


def rolar_teste_atributo(player, atributo, dc):
    atributos = normalizar_atributos(player.get("attributes", {}))
    valor = atributos.get(atributo, 10)
    modificador = calcular_modificador_atributo(valor)
    rolagem = rolar_d20_interativo("Teste de atributo", atributo, dc)
    total = rolagem + modificador

    return {
        "atributo": atributo,
        "rolagem": rolagem,
        "modificador": modificador,
        "total": total,
        "dc": dc,
        "sucesso": total >= dc,
    }


def _aplicar_restauro(player, resource, value):
    current_key = f"current_{resource}"
    max_key = f"max_{resource}"
    max_value = player.get(max_key, 100)
    current_value = player.get(current_key, max_value)
    novo_valor = min(max_value, current_value + value)
    player[current_key] = novo_valor
    return novo_valor - current_value


def resolver_evento_exploracao(player, evento):
    tipo = evento.get("type", "flavor")
    resultado = {
        "type": tipo,
        "title": evento.get("title", "Evento"),
        "text": evento.get("text", ""),
        "messages": [],
        "trigger_combat": False,
    }

    if tipo == "flavor":
        return resultado

    if tipo == "ambush":
        resultado["trigger_combat"] = True
        return resultado

    if tipo == "treasure":
        gold = random.randint(evento.get("gold_min", 1), evento.get("gold_max", 1))
        player["gold"] = player.get("gold", 0) + gold
        salvar_json(PLAYER_PATH, player)
        resultado["messages"].append(f"Voce encontrou {gold}G.")
        return resultado

    if tipo == "secret_quest":
        from src.services.quest_service import aceitar_quest

        quest_id = evento.get("quest_id")
        quest_result = aceitar_quest(player, quest_id)
        resultado["messages"].append(quest_result.get("mensagem", "Nada acontece."))
        return resultado

    if tipo == "resource":
        resource = evento.get("resource", "hp")
        value = int(evento.get("value", 0))
        restored = _aplicar_restauro(player, resource, value)
        salvar_json(PLAYER_PATH, player)
        resultado["messages"].append(f"Voce recuperou {restored} de {resource}.")
        return resultado

    if tipo == "check":
        teste = rolar_teste_atributo(player, evento.get("attribute", "wisdom"), evento.get("dc", 10))
        resultado["check"] = teste
        if teste["sucesso"]:
            resultado["messages"].append(evento.get("success_text", "Voce teve sucesso."))
            gold_min = evento.get("success_gold_min")
            gold_max = evento.get("success_gold_max")
            if gold_min is not None and gold_max is not None:
                gold = random.randint(gold_min, gold_max)
                player["gold"] = player.get("gold", 0) + gold
                resultado["messages"].append(f"Voce encontrou {gold}G.")
        else:
            resultado["messages"].append(evento.get("failure_text", "Voce falhou."))
            damage = int(evento.get("failure_damage", 0))
            if damage > 0:
                player["current_hp"] = max(0, player.get("current_hp", player.get("max_hp", 100)) - damage)
                resultado["messages"].append(f"Voce sofreu {damage} de dano.")
            gold_loss = int(evento.get("failure_gold", 0))
            if gold_loss > 0:
                perda = min(player.get("gold", 0), gold_loss)
                player["gold"] = player.get("gold", 0) - perda
                resultado["messages"].append(f"Voce perdeu {perda}G.")

        salvar_json(PLAYER_PATH, player)
        return resultado

    return resultado


def resolver_evento_urbano(player, contexto):
    village_id = player.get("current_location", "phandalin")
    evento = sortear_evento_urbano(village_id, contexto)
    if not evento:
        return None

    return resolver_evento_exploracao(player, evento)
