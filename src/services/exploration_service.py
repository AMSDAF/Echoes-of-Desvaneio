import random

from src.services.database import salvar_json
from src.services.event_service import (
    carregar_eventos_exploracao,
    resolver_evento_exploracao,
    sortear_evento_exploracao,
)


PLAYER_PATH = "data/core/player.json"
POST_COMBAT_CLUE_CHANCE = 0.10
BASE_COVIL_DISCOVERY_CHANCE = 0.005
KILL_DISCOVERY_BONUS = 0.01
CLUE_DISCOVERY_BONUS = 0.08
MAX_COVIL_DISCOVERY_CHANCE = 0.75


def garantir_estrutura_progresso(player, area_id):
    """Garante que o player tenha o dicionario de progresso para a area atual."""
    if "progresso_areas" not in player:
        player["progresso_areas"] = {}

    if area_id not in player["progresso_areas"]:
        player["progresso_areas"][area_id] = {
            "abates": 0,
            "pistas": 0,
            "boss_hints": [],
            "covil_descoberto": False,
            "chefe_derrotado": False,
        }
        return

    progresso = player["progresso_areas"][area_id]
    progresso.setdefault("abates", 0)
    progresso.setdefault("pistas", 0)
    if "boss_hints" not in progresso or not isinstance(progresso["boss_hints"], list):
        progresso["boss_hints"] = []
    progresso.setdefault("covil_descoberto", False)
    progresso.setdefault("chefe_derrotado", False)


def calcular_chance_descobrir_covil(progresso):
    abates = max(0, int(progresso.get("abates", 0)))
    pistas = max(0, int(progresso.get("pistas", 0)))
    chance = BASE_COVIL_DISCOVERY_CHANCE + (abates * KILL_DISCOVERY_BONUS) + (pistas * CLUE_DISCOVERY_BONUS)
    return min(MAX_COVIL_DISCOVERY_CHANCE, max(0, chance))


def adicionar_pistas(player, area_id, quantidade=1):
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]

    if progresso.get("chefe_derrotado") or progresso.get("covil_descoberto"):
        return {"adicionou": False, "pistas": progresso.get("pistas", 0), "quantidade": 0}

    quantidade = max(1, int(quantidade))
    progresso["pistas"] = max(0, int(progresso.get("pistas", 0))) + quantidade
    salvar_json(PLAYER_PATH, player)
    return {"adicionou": True, "pistas": progresso["pistas"], "quantidade": quantidade}


def revelar_dica_chefe(player, area_id, dica):
    if not dica:
        return {"revelou": False}

    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]
    if progresso.get("chefe_derrotado"):
        return {"revelou": False}

    dica_id = dica.get("id")
    if not dica_id or dica_id in progresso.get("boss_hints", []):
        return {"revelou": False}

    progresso["boss_hints"].append(dica_id)
    salvar_json(PLAYER_PATH, player)
    return {
        "revelou": True,
        "id": dica_id,
        "text": dica.get("text", ""),
        "revealed_hint": dica.get("revealed_hint", ""),
    }


def listar_dicas_chefe_descobertas(player, village_id, area_id):
    garantir_estrutura_progresso(player, area_id)
    ids_descobertos = set(player["progresso_areas"][area_id].get("boss_hints", []))
    if not ids_descobertos:
        return []

    dicas = []
    eventos_area = carregar_eventos_exploracao().get(village_id, {}).get(area_id, [])
    for evento in eventos_area:
        dica = evento.get("boss_hint")
        if dica and dica.get("id") in ids_descobertos:
            dicas.append(dica)
    return dicas


def tentar_encontrar_pista_pos_combate(player, area_id):
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]
    if progresso.get("chefe_derrotado") or progresso.get("covil_descoberto"):
        return {"encontrou": False}

    if random.random() > POST_COMBAT_CLUE_CHANCE:
        return {"encontrou": False}

    resultado = adicionar_pistas(player, area_id, 1)
    return {"encontrou": resultado.get("adicionou", False), **resultado}


def tentar_descobrir_covil(player, area_id):
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]

    if progresso.get("chefe_derrotado"):
        return {"sucesso": False, "chance": 0, "ja_derrotado": True}

    if progresso.get("covil_descoberto"):
        return {"sucesso": True, "chance": 1, "ja_descoberto": True}

    chance = calcular_chance_descobrir_covil(progresso)
    sucesso = random.random() <= chance
    if sucesso:
        progresso["covil_descoberto"] = True
        salvar_json(PLAYER_PATH, player)

    return {
        "sucesso": sucesso,
        "chance": chance,
        "abates": progresso.get("abates", 0),
        "pistas": progresso.get("pistas", 0),
    }


def processar_exploracao(player, area_id, dados_area):
    """Processa encontros, descoberta do boss e achado de ouro."""
    garantir_estrutura_progresso(player, area_id)
    progresso = player["progresso_areas"][area_id]

    if random.random() <= dados_area["encounter_chance"]:
        return {"evento": "combate", "tipo_inimigo": "normal"}

    village_id = player.get("current_location", "phandalin")
    if random.random() <= dados_area.get("event_chance", 0.45):
        evento = sortear_evento_exploracao(village_id, area_id)
        if evento:
            resultado_evento = resolver_evento_exploracao(player, evento, area_id)
            if resultado_evento.get("trigger_combat"):
                return {
                    "evento": "evento_exploracao",
                    "resultado_evento": resultado_evento,
                    "combate_apos_evento": True,
                }

            return {
                "evento": "evento_exploracao",
                "resultado_evento": resultado_evento,
                "combate_apos_evento": False,
            }

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
