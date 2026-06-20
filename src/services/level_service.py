from src.services.database import carregar_json, salvar_json
from src.services.attribute_service import normalizar_atributos


PLAYER_PATH = "data/core/player.json"
SKILLS_PATH = "data/core/skills.json"
HP_BASE = 15
HP_POR_CONSTITUICAO = 2
HP_POR_LEVEL = 6
MANA_BASE = 80
STAMINA_BASE = 80
RECURSO_POR_LEVEL = 15
ATTRIBUTE_POINTS_PER_LEVEL = 3
CLASSES_FISICAS = {"Guerreiro", "Ladino", "Barbaro"}
CLASSES_MAGICAS = {"Mago", "Clerigo", "Druida"}
CLASSES_HIBRIDAS = {"Paladino", "Bardo"}


def calcular_xp_necessario(level):
    return int(100 * (level ** 1.5))


def carregar_skills():
    return carregar_json(SKILLS_PATH) or {"fisico": {}, "magico": {}}


def _categorias_permitidas_por_classe(player):
    nome_classe = (player or {}).get("class", "")
    if nome_classe in CLASSES_FISICAS:
        return {"fisico"}
    if nome_classe in CLASSES_MAGICAS:
        return {"magico"}
    if nome_classe in CLASSES_HIBRIDAS:
        return {"fisico", "magico"}

    return {"fisico", "magico"}


def listar_skill_ids_por_nivel(level, player=None):
    skills_disponiveis = []
    categorias_permitidas = _categorias_permitidas_por_classe(player)
    for categoria, skills in carregar_skills().items():
        if categoria not in categorias_permitidas:
            continue

        for skill_id, skill_data in skills.items():
            if skill_data.get("level_required", 1) <= level:
                skills_disponiveis.append(skill_id)

    return skills_disponiveis


def listar_skill_ids_validas_para_player(player):
    return set(listar_skill_ids_por_nivel(player.get("level", 1), player))


def calcular_status_minimos_por_nivel(player):
    level = max(1, int(player.get("level", 1)))
    atributos = normalizar_atributos(player.get("attributes", {}))
    constituicao = atributos.get("constitution", 10)

    bonus_mana = max(0, atributos.get("intelligence", 10) - 10) * 2
    bonus_stamina = max(0, atributos.get("constitution", 10) - 10) * 2

    return {
        "max_hp": HP_BASE + (constituicao * HP_POR_CONSTITUICAO) + (level * HP_POR_LEVEL),
        "max_mana": MANA_BASE + bonus_mana + ((level - 1) * RECURSO_POR_LEVEL),
        "max_stamina": STAMINA_BASE + bonus_stamina + ((level - 1) * RECURSO_POR_LEVEL),
    }


def sincronizar_status_por_nivel(player):
    modificado = False
    status_minimos = calcular_status_minimos_por_nivel(player)

    for max_key, minimo in status_minimos.items():
        current_key = max_key.replace("max_", "current_")
        valor_atual_max = int(player.get(max_key, minimo))
        valor_atual_current = int(player.get(current_key, valor_atual_max))

        if valor_atual_max != minimo:
            proporcao_atual = 1 if valor_atual_max <= 0 else valor_atual_current / valor_atual_max
            player[max_key] = minimo
            player[current_key] = max(0, min(minimo, int(round(minimo * proporcao_atual))))
            modificado = True
        else:
            player[max_key] = valor_atual_max

        if player.get(current_key, 0) > player[max_key]:
            player[current_key] = player[max_key]
            modificado = True

        if player.get(current_key, 0) < 0:
            player[current_key] = 0
            modificado = True

    return modificado


def garantir_estrutura_evolucao(player):
    modificado = False

    defaults = {
        "level": 1,
        "xp": 0,
        "max_mana": 50,
        "current_mana": 50,
        "max_stamina": 50,
        "current_stamina": 50,
        "known_skills": ["golpe_preciso", "centelha_arcana"],
        "attribute_points": 0,
        "conditions": [],
    }

    for key, value in defaults.items():
        if key not in player:
            player[key] = list(value) if isinstance(value, list) else value
            modificado = True

    if sincronizar_status_por_nivel(player):
        modificado = True

    known_skills = player.setdefault("known_skills", [])
    skills_validas_ordenadas = listar_skill_ids_por_nivel(player.get("level", 1), player)
    skills_validas = set(skills_validas_ordenadas)
    skills_filtradas = [skill_id for skill_id in known_skills if skill_id in skills_validas]
    if skills_filtradas != known_skills:
        player["known_skills"] = skills_filtradas
        known_skills = player["known_skills"]
        modificado = True

    for skill_id in skills_validas_ordenadas:
        if skill_id not in known_skills:
            known_skills.append(skill_id)
            modificado = True

    return modificado


def desbloquear_skills_por_nivel(player):
    known_skills = player.setdefault("known_skills", [])
    novas_skills = []

    for skill_id in listar_skill_ids_por_nivel(player.get("level", 1), player):
        if skill_id not in known_skills:
            known_skills.append(skill_id)
            novas_skills.append(skill_id)

    return novas_skills


def processar_ganho_xp(player, xp_ganho):
    garantir_estrutura_evolucao(player)
    player["xp"] += xp_ganho

    levels_ganhos = 0
    novas_skills = []

    while player["xp"] >= calcular_xp_necessario(player["level"]):
        player["xp"] -= calcular_xp_necessario(player["level"])
        player["level"] += 1
        levels_ganhos += 1
        player["attribute_points"] = player.get("attribute_points", 0) + ATTRIBUTE_POINTS_PER_LEVEL

        status_minimos = calcular_status_minimos_por_nivel(player)
        player["max_hp"] = status_minimos["max_hp"]
        player["max_mana"] = status_minimos["max_mana"]
        player["max_stamina"] = status_minimos["max_stamina"]

        player["current_hp"] = player["max_hp"]
        player["current_mana"] = player["max_mana"]
        player["current_stamina"] = player["max_stamina"]

        novas_skills.extend(desbloquear_skills_por_nivel(player))

    salvar_json(PLAYER_PATH, player)
    return {
        "levels_ganhos": levels_ganhos,
        "novas_skills": novas_skills,
        "xp_atual": player["xp"],
        "xp_proximo": calcular_xp_necessario(player["level"]),
    }


def gastar_ponto_atributo(player, atributo, quantidade=1):
    quantidade = max(1, int(quantidade))
    pontos = int(player.get("attribute_points", 0))
    atributos = normalizar_atributos(player.get("attributes", {}))

    if atributo not in atributos:
        return {"sucesso": False, "mensagem": "Atributo invalido."}

    if pontos < quantidade:
        return {"sucesso": False, "mensagem": "Pontos de atributo insuficientes."}

    atributos[atributo] += quantidade
    player["attributes"] = atributos
    player["attribute_points"] = pontos - quantidade
    sincronizar_status_por_nivel(player)
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True, "mensagem": "Atributo aprimorado."}
