import random

from src.services.city_data_service import carregar_npcs_cidade
from src.services.database import salvar_json
from src.services.quest_service import aceitar_quest, obter_estado_quest, obter_quest


PLAYER_PATH = "data/core/player.json"


def carregar_npcs(village_id):
    return carregar_npcs_cidade(village_id)


def garantir_memoria_npcs(player):
    if "npc_memory" not in player or not isinstance(player["npc_memory"], dict):
        player["npc_memory"] = {}
        return True

    return False


def listar_npcs_vila(village_id):
    dados = carregar_npcs(village_id)
    return dados.get("npcs", {})


def obter_npc(village_id, npc_id):
    return listar_npcs_vila(village_id).get(npc_id)


def obter_memoria_npc(player, npc_id):
    garantir_memoria_npcs(player)
    memoria = player["npc_memory"].setdefault(
        npc_id,
        {
            "talk_count": 0,
            "affinity": 0,
            "known_topics": [],
        },
    )
    return memoria


def registrar_conversa(player, npc_id, topic_id=None):
    memoria = obter_memoria_npc(player, npc_id)
    memoria["talk_count"] = memoria.get("talk_count", 0) + 1
    memoria["affinity"] = min(100, memoria.get("affinity", 0) + 1)

    if topic_id:
        topicos = memoria.setdefault("known_topics", [])
        if topic_id not in topicos:
            topicos.append(topic_id)

    salvar_json(PLAYER_PATH, player)
    return memoria


def obter_saudacao(npc, memoria):
    if memoria.get("talk_count", 0) <= 0:
        return npc.get("greeting", "Bem-vindo.")

    afinidade = memoria.get("affinity", 0)
    if afinidade >= 8:
        return "Bom te ver de novo. Pouca gente volta com os mesmos olhos depois da estrada."

    return "Voce de novo. Isso costuma significar problema, noticia ou os dois."


def obter_rumor_npc(npc):
    rumores = npc.get("rumors", [])
    if not rumores:
        return "Nao ouvi nada que valha uma moeda hoje."

    return random.choice(rumores)


def listar_topicos_npc(npc):
    return list(npc.get("topics", {}).items())


def obter_texto_topico(npc, topic_id):
    return npc.get("topics", {}).get(topic_id, "Esse assunto ainda nao leva a lugar nenhum.")


def listar_quests_npc(player, npc):
    quests = []
    for quest_id in npc.get("quest_ids", []):
        _, quest = obter_quest(quest_id, player=player)
        if not quest:
            continue

        estado = obter_estado_quest(player, quest_id)
        quests.append((quest_id, quest, estado))

    return quests


def tentar_aceitar_quest_npc(player, quest_id):
    return aceitar_quest(player, quest_id)
