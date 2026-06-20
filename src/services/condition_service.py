import random

from src.services.attribute_service import calcular_modificador_atributo, normalizar_atributos
from src.services.dice_service import rolar_d20_interativo


CONDITIONS = {
    "bleeding": {
        "name": "Sangrando",
        "description": "Sofre dano no inicio do turno.",
        "type": "damage_over_time",
    },
    "poisoned": {
        "name": "Envenenado",
        "description": "Sofre dano no inicio do turno.",
        "type": "damage_over_time",
    },
    "burning": {
        "name": "Queimando",
        "description": "Sofre dano no inicio do turno.",
        "type": "damage_over_time",
    },
    "stunned": {
        "name": "Atordoado",
        "description": "Reduz reacoes defensivas.",
        "type": "defense_penalty",
    },
    "blessed": {
        "name": "Abencoado",
        "description": "Aumenta a chance critica.",
        "type": "crit_bonus",
    },
    "fortified": {
        "name": "Fortificado",
        "description": "Reduz dano recebido.",
        "type": "damage_reduction",
    },
    "exhausted": {
        "name": "Exausto",
        "description": "Aumenta custos de Estamina.",
        "type": "resource_penalty",
    },
    "silenced": {
        "name": "Silenciado",
        "description": "Impede habilidades magicas.",
        "type": "skill_lock",
    },
    "corroded": {
        "name": "Corroido",
        "description": "Aumenta desgaste de armadura.",
        "type": "durability_penalty",
    },
}


def garantir_condicoes(entidade):
    if "conditions" not in entidade or not isinstance(entidade["conditions"], list):
        entidade["conditions"] = []


def obter_nome_condicao(condition_id):
    return CONDITIONS.get(condition_id, {}).get("name", condition_id)


def rolar_resistencia(atributos, save, bonus_extra=0):
    if not save:
        return {"tentou": False, "sucesso": False}

    atributo = save.get("attribute", "constitution")
    dc = int(save.get("dc", 10))
    atributos = normalizar_atributos(atributos or {})
    modificador = calcular_modificador_atributo(atributos.get(atributo, 10))
    rolagem = rolar_d20_interativo("Teste de resistencia", atributo, dc)
    try:
        bonus_extra = int(bonus_extra)
    except (TypeError, ValueError):
        bonus_extra = 0
    total = rolagem + modificador + bonus_extra

    return {
        "tentou": True,
        "attribute": atributo,
        "dc": dc,
        "roll": rolagem,
        "modifier": modificador,
        "bonus_extra": bonus_extra,
        "total": total,
        "sucesso": total >= dc,
    }


def adicionar_condicao(entidade, condition_spec):
    garantir_condicoes(entidade)
    condition_id = condition_spec.get("id")
    if condition_id not in CONDITIONS:
        return None

    nova_condicao = {
        "id": condition_id,
        "name": obter_nome_condicao(condition_id),
        "duration": max(1, int(condition_spec.get("duration", 1))),
        "potency": condition_spec.get("potency", 1),
    }

    for condicao in entidade["conditions"]:
        if condicao.get("id") == condition_id:
            condicao["duration"] = max(condicao.get("duration", 1), nova_condicao["duration"])
            condicao["potency"] = max(float(condicao.get("potency", 0)), float(nova_condicao["potency"]))
            return condicao

    entidade["conditions"].append(nova_condicao)
    return nova_condicao


def tentar_aplicar_condicao(entidade, condition_spec, atributos_alvo=None, bonus_resistencia=0):
    if not condition_spec:
        return {"aplicada": False, "mensagem": None}

    chance = float(condition_spec.get("chance", 1))
    if random.random() > chance:
        return {"aplicada": False, "mensagem": None}

    save = rolar_resistencia(atributos_alvo, condition_spec.get("save"), bonus_resistencia)
    nome = obter_nome_condicao(condition_spec.get("id"))
    if save.get("tentou") and save.get("sucesso"):
        sinal = "+" if save["modifier"] >= 0 else ""
        bonus = f" +{save['bonus_extra']}" if save.get("bonus_extra", 0) > 0 else ""
        return {
            "aplicada": False,
            "mensagem": (
                f"Resistiu a {nome}: d20({save['roll']}) {sinal}{save['modifier']}{bonus} "
                f"= {save['total']} vs CD {save['dc']}."
            ),
        }

    condicao = adicionar_condicao(entidade, condition_spec)
    if not condicao:
        return {"aplicada": False, "mensagem": None}

    mensagem = f"{entidade.get('name', 'Alvo')} ficou {condicao['name']} por {condicao['duration']} turnos."
    if save.get("tentou"):
        sinal = "+" if save["modifier"] >= 0 else ""
        bonus = f" +{save['bonus_extra']}" if save.get("bonus_extra", 0) > 0 else ""
        mensagem += f" Falhou no teste: d20({save['roll']}) {sinal}{save['modifier']}{bonus} = {save['total']} vs CD {save['dc']}."

    return {"aplicada": True, "mensagem": mensagem}


def processar_condicoes_inicio_turno(entidade):
    garantir_condicoes(entidade)
    mensagens = []
    dano_total = 0
    restantes = []

    for condicao in entidade["conditions"]:
        condition_id = condicao.get("id")
        nome = condicao.get("name", obter_nome_condicao(condition_id))
        potencia = condicao.get("potency", 1)

        if CONDITIONS.get(condition_id, {}).get("type") == "damage_over_time":
            dano = max(1, int(potencia))
            entidade["current_hp"] = max(0, entidade.get("current_hp", 0) - dano)
            dano_total += dano
            mensagens.append(f"{entidade.get('name', 'Alvo')} sofre {dano} de dano por {nome}.")

        condicao["duration"] = int(condicao.get("duration", 1)) - 1
        if condicao["duration"] > 0:
            restantes.append(condicao)
        else:
            mensagens.append(f"{nome} terminou em {entidade.get('name', 'Alvo')}.")

    entidade["conditions"] = restantes
    return {"dano_total": dano_total, "mensagens": mensagens}


def entidade_tem_condicao(entidade, condition_id):
    return any(condicao.get("id") == condition_id for condicao in entidade.get("conditions", []))


def obter_potencia_condicao(entidade, condition_id, padrao=0):
    for condicao in entidade.get("conditions", []):
        if condicao.get("id") == condition_id:
            return condicao.get("potency", padrao)

    return padrao


def aplicar_reducao_dano_por_condicoes(entidade, dano):
    reducao = float(obter_potencia_condicao(entidade, "fortified", 0))
    if reducao <= 0:
        return dano

    return max(0, int(round(dano * (1 - reducao))))


def calcular_bonus_critico_condicoes(entidade):
    return float(obter_potencia_condicao(entidade, "blessed", 0))


def calcular_penalidade_reacao_condicoes(entidade):
    if entidade_tem_condicao(entidade, "stunned"):
        return 0.12

    return 0


def calcular_multiplicador_custo_recurso(entidade, resource):
    if resource == "stamina" and entidade_tem_condicao(entidade, "exhausted"):
        return 1.5

    return 1


def calcular_multiplicador_desgaste(entidade):
    if entidade_tem_condicao(entidade, "corroded"):
        return 2

    return 1


def remove_condicao(entidade, condition_id):
    garantir_condicoes(entidade)
    antes = len(entidade["conditions"])
    entidade["conditions"] = [
        condicao for condicao in entidade["conditions"]
        if condicao.get("id") != condition_id
    ]
    return len(entidade["conditions"]) != antes
