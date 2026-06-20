import random

from src.services.database import salvar_json


PLAYER_PATH = "data/core/player.json"


def garantir_estrutura_progresso(player, area_id):
    """Garante que o player tenha o dicionario de progresso para a area atual."""
    if "progresso_areas" not in player:
        player["progresso_areas"] = {}

    if area_id not in player["progresso_areas"]:
        player["progresso_areas"][area_id] = {
            "abates": 0,
            "covil_descoberto": False,
            "chefe_derrotado": False,
        }


def processar_exploracao(player, area_id, dados_area):
    """Processa encontros, descoberta do boss e achado de ouro."""
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]

    if random.random() <= dados_area["encounter_chance"]:
        return {"evento": "combate", "tipo_inimigo": "normal"}

    if not progresso["covil_descoberto"] and not progresso["chefe_derrotado"]:
        if random.random() <= 0.05:
            progresso["covil_descoberto"] = True
            salvar_json(PLAYER_PATH, player)
            return {"evento": "covil_encontrado"}

    ouro_achado = 0
    if random.random() <= 0.20:
        ouro_achado = random.randint(5, 15)
        player["gold"] += ouro_achado

    salvar_json(PLAYER_PATH, player)
    return {"evento": "seguro", "ouro_achado": ouro_achado}


def tentar_acampar(player):
    """Verifica se o player possui o kit de fogueira para restaurar vida."""
    kit_fogueira = next(
        (item for item in player.get("inventory", []) if item.get("id") == "kit_fogueira"),
        None,
    )

    if not kit_fogueira:
        return {"sucesso": False}

    player["inventory"].remove(kit_fogueira)
    player["current_hp"] = player.get("max_hp", 100)
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True}


def tentar_avancar_cidade(player, area_id, dados_area):
    """Tenta transicionar para a proxima vila liberada pelo boss da area."""
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]

    if not dados_area.get("boss_unlocks_next_village", False):
        return {"status": "sem_proxima_cidade"}

    next_village_id = dados_area.get("next_village_id")
    if not next_village_id:
        return {"status": "sem_proxima_cidade"}

    if progresso["chefe_derrotado"]:
        player["current_location"] = next_village_id
        salvar_json(PLAYER_PATH, player)
        return {"status": "sucesso_transicao", "nova_vila": next_village_id}

    return {
        "status": "barrado_pelo_boss",
        "pode_fugir": False,
        "boss": dados_area["boss"],
    }


def processar_retirada(player, dados_area):
    """Voltar para a cidade gera um risco menor de emboscada."""
    chance_retirada = min(dados_area.get("encounter_chance", 0.15), 0.15)

    if random.random() <= chance_retirada:
        return {"evento": "combate"}

    return {"evento": "seguro"}
