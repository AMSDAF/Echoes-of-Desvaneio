from src.services.database import carregar_json, salvar_json
from src.services.level_service import processar_ganho_xp


PLAYER_PATH = "data/core/player.json"
QUESTS_PATH = "data/core/quests.json"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_CLAIMED = "reward_claimed"


def carregar_quests():
    return carregar_json(QUESTS_PATH) or {}


def garantir_quest_log(player):
    if "quest_log" not in player or not isinstance(player["quest_log"], dict):
        player["quest_log"] = {}
        return True

    return False


def listar_quests_vila(village_id):
    dados = carregar_quests().get(village_id, {})
    return dados.get("quests", {})


def obter_quest(quest_id):
    for village_id, village_data in carregar_quests().items():
        quest = village_data.get("quests", {}).get(quest_id)
        if quest:
            return village_id, quest

    return None, None


def obter_estado_quest(player, quest_id):
    garantir_quest_log(player)
    return player["quest_log"].get(quest_id)


def _criar_progresso_inicial(quest):
    return {
        objective["id"]: 0
        for objective in quest.get("objectives", [])
    }


def aceitar_quest(player, quest_id):
    _, quest = obter_quest(quest_id)
    if not quest:
        return {"sucesso": False, "mensagem": "Missao nao encontrada."}

    garantir_quest_log(player)
    estado = player["quest_log"].get(quest_id)
    if estado:
        return {"sucesso": False, "mensagem": "Essa missao ja esta no seu diario."}

    player["quest_log"][quest_id] = {
        "status": STATUS_ACTIVE,
        "progress": _criar_progresso_inicial(quest),
    }
    salvar_json(PLAYER_PATH, player)
    return {"sucesso": True, "mensagem": f"Missao aceita: {quest['title']}."}


def _objetivo_concluido(objective, progress):
    return progress.get(objective["id"], 0) >= objective.get("required", 1)


def quest_esta_concluida(quest, progress):
    return all(
        _objetivo_concluido(objective, progress)
        for objective in quest.get("objectives", [])
    )


def registrar_abate_quest(player, enemy_id):
    garantir_quest_log(player)
    mensagens = []
    modificado = False

    for quest_id, estado in player["quest_log"].items():
        if estado.get("status") != STATUS_ACTIVE:
            continue

        _, quest = obter_quest(quest_id)
        if not quest:
            continue

        progress = estado.setdefault("progress", {})
        for objective in quest.get("objectives", []):
            if objective.get("type") != "kill":
                continue

            if enemy_id not in objective.get("enemy_ids", []):
                continue

            objective_id = objective["id"]
            atual = progress.get(objective_id, 0)
            requerido = objective.get("required", 1)
            if atual < requerido:
                progress[objective_id] = min(requerido, atual + 1)
                mensagens.append(
                    f"{quest['title']}: {objective['label']} "
                    f"({progress[objective_id]}/{requerido})"
                )
                modificado = True

        if quest_esta_concluida(quest, progress):
            estado["status"] = STATUS_COMPLETED
            mensagens.append(f"Missao concluida: {quest['title']}! Volte ao quadro para receber a recompensa.")
            modificado = True

    if modificado:
        salvar_json(PLAYER_PATH, player)

    return mensagens


def entregar_quest(player, quest_id):
    garantir_quest_log(player)
    estado = player["quest_log"].get(quest_id)
    _, quest = obter_quest(quest_id)

    if not estado or not quest:
        return {"sucesso": False, "mensagem": "Missao nao encontrada no diario."}

    if estado.get("status") != STATUS_COMPLETED:
        return {"sucesso": False, "mensagem": "Essa missao ainda nao foi concluida."}

    rewards = quest.get("rewards", {})
    gold = int(rewards.get("gold", 0))
    xp = int(rewards.get("xp", 0))

    player["gold"] = player.get("gold", 0) + gold
    estado["status"] = STATUS_CLAIMED
    resultado_xp = processar_ganho_xp(player, xp) if xp > 0 else None
    salvar_json(PLAYER_PATH, player)

    return {
        "sucesso": True,
        "title": quest["title"],
        "gold": gold,
        "xp": xp,
        "resultado_xp": resultado_xp,
    }


def formatar_progresso_quest(quest, estado):
    progress = (estado or {}).get("progress", {})
    linhas = []

    for objective in quest.get("objectives", []):
        atual = progress.get(objective["id"], 0)
        requerido = objective.get("required", 1)
        linhas.append(f"{objective['label']}: {atual}/{requerido}")

    return linhas
