import random

from src.services.attribute_service import calcular_modificador_atributo
from src.services.database import carregar_json, salvar_json
from src.services.level_service import garantir_estrutura_evolucao, processar_ganho_xp


PLAYER_PATH = "data/core/player.json"
ENEMIES_PATH = "data/enemies/enemies.json"
RACES_PATH = "data/core/races.json"
SKILLS_PATH = "data/core/skills.json"
DANO_BASE_PADRAO = 10
CHANCE_CRITICO_BASE = 0.05


def carregar_dados_monstro(enemy_id):
    """Busca os atributos base do monstro no banco de dados."""
    inimigos = carregar_json(ENEMIES_PATH) or {}
    return inimigos.get(enemy_id)


def carregar_dados_racas():
    return carregar_json(RACES_PATH) or {}


def carregar_dados_skills():
    return carregar_json(SKILLS_PATH) or {"fisico": {}, "magico": {}}


def listar_habilidades_conhecidas(player, categoria):
    garantir_estrutura_evolucao(player)
    skills_categoria = carregar_dados_skills().get(categoria, {})
    known_skills = set(player.get("known_skills", []))

    return [
        {"id": skill_id, "category": categoria, **skill_data}
        for skill_id, skill_data in skills_categoria.items()
        if skill_id in known_skills
    ]


def obter_habilidade(skill_id, categoria):
    skill_data = carregar_dados_skills().get(categoria, {}).get(skill_id)
    if not skill_data:
        return None

    return {"id": skill_id, "category": categoria, **skill_data}


def jogador_tem_recurso_para_habilidade(player, habilidade):
    cost = habilidade.get("cost", {})
    resource = cost.get("resource")
    value = cost.get("value", 0)
    current_key = f"current_{resource}"

    return player.get(current_key, 0) >= value


def consumir_recurso_habilidade(player, habilidade):
    cost = habilidade.get("cost", {})
    resource = cost.get("resource")
    value = cost.get("value", 0)
    current_key = f"current_{resource}"

    if not resource or not jogador_tem_recurso_para_habilidade(player, habilidade):
        return False

    player[current_key] -= value
    salvar_json(PLAYER_PATH, player)
    return True


def obter_efeitos_raciais(player):
    """Retorna os efeitos numericos da passiva racial salva no player."""
    raca_player = str(player.get("race", "")).lower()
    if not raca_player:
        return {}

    for race_key, race_data in carregar_dados_racas().items():
        nomes_possiveis = {race_key.lower(), str(race_data.get("name", "")).lower()}
        if raca_player in nomes_possiveis:
            return race_data.get("passive", {}).get("effects", {})

    return {}


def _obter_atributo(atributos, nome, padrao=10):
    return (atributos or {}).get(nome, padrao)


def _obter_efeito(efeitos_raciais, nome, padrao=0):
    return (efeitos_raciais or {}).get(nome, padrao)


def calcular_chance_esquiva(atributos_defensor, efeitos_raciais=None):
    mod_dex = calcular_modificador_atributo(_obter_atributo(atributos_defensor, "dexterity"))
    luck = _obter_atributo(atributos_defensor, "luck", 0)
    bonus_racial = _obter_efeito(efeitos_raciais, "dodge_chance_bonus")
    return min(0.90, max(0.0, 0.50 + (mod_dex * 0.04) + (luck * 0.02) + bonus_racial))


def calcular_percentual_dano_bloqueio(atributos_defensor, efeitos_raciais=None):
    mod_const = calcular_modificador_atributo(_obter_atributo(atributos_defensor, "constitution"))
    reducao_racial = _obter_efeito(efeitos_raciais, "block_damage_factor_reduction")
    return max(0.10, 0.40 - (mod_const * 0.02) - reducao_racial)


def calcular_chance_contra_ataque(atributos_defensor, efeitos_raciais=None):
    mod_dex = calcular_modificador_atributo(_obter_atributo(atributos_defensor, "dexterity"))
    luck = _obter_atributo(atributos_defensor, "luck", 0)
    bonus_racial = _obter_efeito(efeitos_raciais, "counter_chance_bonus")
    return min(0.75, max(0.0, 0.35 + (mod_dex * 0.03) + (luck * 0.03) + bonus_racial))


def calcular_chance_fuga(atributos_player, efeitos_raciais=None):
    mod_dex = calcular_modificador_atributo(_obter_atributo(atributos_player, "dexterity"))
    luck = _obter_atributo(atributos_player, "luck", 0)
    bonus_racial = _obter_efeito(efeitos_raciais, "escape_chance_bonus")
    return min(1.0, max(0.0, 0.40 + (mod_dex * 0.05) + (luck * 0.02) + bonus_racial))


def calcular_chance_critico(efeitos_raciais=None):
    bonus_racial = _obter_efeito(efeitos_raciais, "critical_chance_bonus")
    return min(1.0, max(0.0, CHANCE_CRITICO_BASE + bonus_racial))


def calcular_dano_base(atacante_atributos, tipo_ataque, efeitos_raciais=None):
    """Calcula o dano bruto inicial com modificador D&D e passivas raciais."""
    atributo = "intelligence" if tipo_ataque == "magia" else "strength"
    modificador = calcular_modificador_atributo(_obter_atributo(atacante_atributos, atributo))
    dano = max(1, DANO_BASE_PADRAO + modificador)

    if tipo_ataque == "magia":
        dano *= _obter_efeito(efeitos_raciais, "magic_damage_multiplier", 1)
    else:
        dano *= _obter_efeito(efeitos_raciais, "physical_damage_multiplier", 1)

    return max(1, int(round(dano)))


def calcular_dano_habilidade(atacante_atributos, tipo_ataque, habilidade, efeitos_raciais=None):
    dano_base = calcular_dano_base(atacante_atributos, tipo_ataque, efeitos_raciais)
    multiplier = habilidade.get("multiplier", 1)
    return max(1, int(round(dano_base * multiplier)))


def aplicar_mitigacao_dano_recebido(dano_bruto, tipo_dano, efeitos_raciais=None):
    if tipo_dano == "magia":
        dano_bruto *= _obter_efeito(efeitos_raciais, "magic_damage_received_multiplier", 1)

    return max(1, int(round(dano_bruto)))


def processar_defesa(
    dano_bruto,
    postura_defesa,
    defesa_defensor=0,
    atributos_defensor=None,
    efeitos_raciais=None,
    tipo_dano="fisico",
):
    """
    Processa a reacao do defensor a um ataque recebido.
    Retorna uma tupla: (dano_recebido, dano_contra_ataque, mensagem)
    """
    dano_mitigado = aplicar_mitigacao_dano_recebido(dano_bruto, tipo_dano, efeitos_raciais)
    dano_real = max(1, dano_mitigado - defesa_defensor)

    if postura_defesa == "esquivar":
        chance_esquiva = calcular_chance_esquiva(atributos_defensor, efeitos_raciais)
        if random.random() <= chance_esquiva:
            return 0, 0, "Esquiva perfeita! Nenhum dano recebido."

        return int(dano_real * 0.5), 0, "Falhou na esquiva, mas minimizou o impacto! Recebeu 50% do dano."

    if postura_defesa == "bloquear":
        percentual_dano = calcular_percentual_dano_bloqueio(atributos_defensor, efeitos_raciais)
        dano_recebido = int(dano_real * percentual_dano)
        percentual_texto = int(round(percentual_dano * 100))
        return dano_recebido, 0, f"Bloqueou o impacto! Recebeu apenas {percentual_texto}% do dano."

    if postura_defesa == "contra_atacar":
        chance_contra_ataque = calcular_chance_contra_ataque(atributos_defensor, efeitos_raciais)
        if random.random() <= chance_contra_ataque:
            dano_devolvido = int(dano_bruto * 0.5)
            return 0, dano_devolvido, f"Contra-ataque critico! Evitou o golpe e revidou causando {dano_devolvido} de dano!"

        dano_punicao = int(dano_real * 1.25)
        return dano_punicao, 0, "Falhou no contra-ataque! Ficou vulneravel e recebeu 125% de dano!"

    return dano_real, 0, "Recebeu o golpe em cheio!"


def calcular_desgaste_arma(player):
    """Aplica o desgaste de durabilidade na arma equipada caso exista."""
    arma = player.get("equipped", {}).get("weapon")
    if arma and "durability" in arma:
        arma["durability"] = max(0, arma["durability"] - 1)


def processar_vitoria(player, dados_monstro):
    """Aplica as recompensas de XP, Ouro e rola a tabela de loot para materiais."""
    processar_ganho_xp(player, dados_monstro["xp_drop"])
    player["gold"] += dados_monstro["gold_drop"]

    materiais_ganhos = []
    luck = player.get("attributes", {}).get("luck", 0)
    bonus_luck = luck * 0.015

    for loot in dados_monstro.get("loot_table", []):
        chance_final = min(1.0, loot["chance"] + bonus_luck)
        if random.random() <= chance_final:
            item_material = {
                "id": loot["item_id"],
                "name": loot["item_id"].replace("_", " ").title(),
                "type": "material",
            }
            player["inventory"].append(item_material)
            materiais_ganhos.append(item_material["name"])

    salvar_json(PLAYER_PATH, player)
    return materiais_ganhos
