from src.services.database import carregar_json
from src.services.attribute_service import normalizar_atributos


CLASSES_FISICAS = {"Guerreiro", "Ladino", "Barbaro"}
CLASSES_MAGICAS = {"Mago", "Clerigo", "Druida"}
HP_BASE = 15
HP_POR_CONSTITUICAO = 2
HP_POR_LEVEL = 6
MANA_BASE = 50
STAMINA_BASE = 50


def obter_classes_disponiveis():
    return carregar_json("data/core/class.json")

def obter_racas_disponiveis():
    return carregar_json("data/core/races.json")

def validar_distribuicao_pontos(atributo_atual, pontos_desejados, pontos_restantes):
    if 0 < pontos_desejados <= pontos_restantes:
        return True, pontos_restantes - pontos_desejados
    return False, pontos_restantes

def aplicar_bonus_racial(atributos, raca_dados):
    atributos_com_bonus = normalizar_atributos(atributos)
    bonus_racial = (raca_dados or {}).get("attribute_bonuses", {})

    for attr, bonus in bonus_racial.items():
        if attr in atributos_com_bonus:
            atributos_com_bonus[attr] += bonus

    return atributos_com_bonus


def determinar_habilidades_iniciais(classe_dados):
    nome_classe = classe_dados.get("name", "")

    if nome_classe in CLASSES_FISICAS:
        return ["golpe_preciso", "investida_pesada"]

    if nome_classe in CLASSES_MAGICAS:
        return ["centelha_arcana", "lanca_eterea"]

    return ["golpe_preciso", "centelha_arcana"]


def construir_personagem_inicial(name, classe_dados, raca_dados, atributos_finais):
    atributos_finais = normalizar_atributos(atributos_finais)
    atributos_finais = aplicar_bonus_racial(atributos_finais, raca_dados)
    constituicao = atributos_finais.get("constitution", 10)
    inteligencia = atributos_finais.get("intelligence", 10)
    max_hp = HP_BASE + (constituicao * HP_POR_CONSTITUICAO) + HP_POR_LEVEL
    max_mana = MANA_BASE + (max(0, inteligencia - 10) * 2)
    max_stamina = STAMINA_BASE + (max(0, constituicao - 10) * 2)

    return {
        "name": name,
        "class": classe_dados['name'],
        "race": raca_dados["name"],
        "level": 1,
        "xp": 0,
        "gold": 90,
        "current_hp": max_hp,
        "max_hp": max_hp,
        "current_mana": max_mana,
        "max_mana": max_mana,
        "current_stamina": max_stamina,
        "max_stamina": max_stamina,
        "known_skills": determinar_habilidades_iniciais(classe_dados),
        "skill_points": 0,
        "skill_upgrades": {},
        "attribute_points": 0,
        "conditions": [],
        "current_location": "oakridge",
        "unlocked_villages": {
            "oakridge": True
        },
        "attributes": atributos_finais,
        "equipped": {
            "helmet": None, "breastplate": None, "pants": None,
            "boots": None, "shield": None, "ring": None, "necklace": None, "weapon": None
        },
        "inventory": [],
        "progresso_areas": {}
    }
