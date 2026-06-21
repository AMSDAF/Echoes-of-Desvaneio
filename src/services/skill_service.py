from copy import deepcopy

from src.services.database import salvar_json
from src.services.level_service import carregar_skills, garantir_estrutura_evolucao


PLAYER_PATH = "data/core/player.json"

RARITY_MAX_UPGRADES = {
    "comum": 3,
    "incomum": 2,
    "raro": 2,
    "epico": 1,
    "lendario": 1,
}


def _todos_os_dados_skills():
    return carregar_skills() or {"fisico": {}, "magico": {}}


def _obter_upgrade_count(player, skill_id):
    upgrades = player.setdefault("skill_upgrades", {})
    if not isinstance(upgrades, dict):
        player["skill_upgrades"] = {}
        upgrades = player["skill_upgrades"]
    try:
        return max(0, int(upgrades.get(skill_id, 0)))
    except (TypeError, ValueError):
        upgrades[skill_id] = 0
        return 0


def _max_upgrades(habilidade):
    raridade = str(habilidade.get("rarity", "comum")).lower()
    return RARITY_MAX_UPGRADES.get(raridade, 1)


def aplicar_progresso_habilidade(player, skill_id, categoria, habilidade_base):
    habilidade = deepcopy(habilidade_base)
    upgrades = _obter_upgrade_count(player, skill_id)
    habilidade["id"] = skill_id
    habilidade["category"] = categoria
    habilidade["base_skill_level"] = habilidade.get("skill_level", 1)
    habilidade["upgrade_count"] = upgrades
    habilidade["max_upgrades"] = _max_upgrades(habilidade)
    habilidade["skill_level"] = habilidade["base_skill_level"] + upgrades

    multiplier = float(habilidade.get("multiplier", 1))
    habilidade["multiplier"] = round(multiplier + (upgrades * 0.12), 2)

    condicao = habilidade.get("applies_condition")
    if condicao:
        condicao = deepcopy(condicao)
        condicao["chance"] = round(min(0.75, float(condicao.get("chance", 0)) + (upgrades * 0.04)), 2)
        if upgrades >= 2:
            condicao["duration"] = int(condicao.get("duration", 1)) + 1
        habilidade["applies_condition"] = condicao

    return habilidade


def listar_habilidades_conhecidas_detalhadas(player, categoria=None):
    garantir_estrutura_evolucao(player)
    known_skills = set(player.get("known_skills", []))
    habilidades = []

    for cat, skills in _todos_os_dados_skills().items():
        if categoria and cat != categoria:
            continue

        for skill_id, skill_data in skills.items():
            if skill_id not in known_skills:
                continue
            habilidades.append(aplicar_progresso_habilidade(player, skill_id, cat, skill_data))

    return habilidades


def obter_habilidade_conhecida(player, skill_id):
    for habilidade in listar_habilidades_conhecidas_detalhadas(player):
        if habilidade.get("id") == skill_id:
            return habilidade
    return None


def calcular_custo_treino_habilidade(player, habilidade):
    return 1 + _obter_upgrade_count(player, habilidade.get("id"))


def treinar_habilidade(player, skill_id):
    garantir_estrutura_evolucao(player)
    habilidade = obter_habilidade_conhecida(player, skill_id)
    if not habilidade:
        return {"sucesso": False, "mensagem": "Voce ainda nao conhece essa habilidade."}

    upgrades = _obter_upgrade_count(player, skill_id)
    max_upgrades = habilidade.get("max_upgrades", _max_upgrades(habilidade))
    if upgrades >= max_upgrades:
        return {"sucesso": False, "mensagem": "Essa habilidade ja atingiu o limite de treino atual."}

    custo = calcular_custo_treino_habilidade(player, habilidade)
    pontos = max(0, int(player.get("skill_points", 0)))
    if pontos < custo:
        return {"sucesso": False, "mensagem": f"Ainda nao tenho foco suficiente para lapidar isso. Preciso de {custo} ponto(s)."}

    player["skill_points"] = pontos - custo
    player.setdefault("skill_upgrades", {})[skill_id] = upgrades + 1
    salvar_json(PLAYER_PATH, player)

    habilidade_atualizada = obter_habilidade_conhecida(player, skill_id)
    return {
        "sucesso": True,
        "mensagem": f"Sinto {habilidade_atualizada['name']} encaixar melhor nas minhas maos. Agora ela esta no Nv. {habilidade_atualizada['skill_level']}.",
        "habilidade": habilidade_atualizada,
    }
