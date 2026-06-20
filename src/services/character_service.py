from src.services.database import carregar_json

def obter_classes_disponiveis():
    return carregar_json("data/class.json")

def validar_distribuicao_pontos(atributo_atual, pontos_desejados, pontos_restantes):
    if 0 < pontos_desejados <= pontos_restantes:
        return True, pontos_restantes - pontos_desejados
    return False, pontos_restantes

def construir_personagem_inicial(name, classe_dados, atributos_finais):
    vitalidade = atributos_finais.get("vitality", 10)
    max_hp = 80 + (vitalidade * 5)

    return {
        "name": name,
        "class": classe_dados['name'],
        "level": 1,
        "xp": 0,
        "gold": 250,
        "current_hp": max_hp,
        "max_hp": max_hp,
        "current_location": "phandalin",
        "attributes": atributos_finais,
        "equipped": {
            "helmet": None, "breastplate": None, "pants": None,
            "boots": None, "ring": None, "necklace": None, "weapon": None
        },
        "inventory": [],
        "progresso_areas": {}
    }