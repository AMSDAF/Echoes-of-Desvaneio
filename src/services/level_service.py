from src.services.database import carregar_json, salvar_json


PLAYER_PATH = "data/core/player.json"
SKILLS_PATH = "data/core/skills.json"


def calcular_xp_necessario(level):
    return int(100 * (level ** 1.5))


def carregar_skills():
    return carregar_json(SKILLS_PATH) or {"fisico": {}, "magico": {}}


def listar_skill_ids_por_nivel(level):
    skills_disponiveis = []
    for categoria, skills in carregar_skills().items():
        for skill_id, skill_data in skills.items():
            if skill_data.get("level_required", 1) <= level:
                skills_disponiveis.append(skill_id)

    return skills_disponiveis


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
    }

    for key, value in defaults.items():
        if key not in player:
            player[key] = list(value) if isinstance(value, list) else value
            modificado = True

    return modificado


def desbloquear_skills_por_nivel(player):
    garantir_estrutura_evolucao(player)
    known_skills = player.setdefault("known_skills", [])
    novas_skills = []

    for skill_id in listar_skill_ids_por_nivel(player.get("level", 1)):
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

        player["max_hp"] = player.get("max_hp", 100) + 12
        player["max_mana"] = player.get("max_mana", 50) + 10
        player["max_stamina"] = player.get("max_stamina", 50) + 10

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
