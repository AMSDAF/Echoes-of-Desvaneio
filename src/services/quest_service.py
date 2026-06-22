from src.services.city_data_service import CITIES_ROOT, carregar_quests_cidade
from src.services.database import salvar_json
from src.services.level_service import processar_ganho_xp


PLAYER_PATH = "data/core/player.json"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_CLAIMED = "reward_claimed"


def carregar_quests(village_id):
    return carregar_quests_cidade(village_id)


def _listar_ids_cidades():
    if not CITIES_ROOT.exists():
        return []

    city_ids = []
    for folder in CITIES_ROOT.iterdir():
        if not folder.is_dir():
            continue

        nome = folder.name
        if ". " in nome:
            nome = nome.split(". ", 1)[1]
        city_ids.append(nome.strip().lower())

    return city_ids


def garantir_quest_log(player):
    if "quest_log" not in player or not isinstance(player["quest_log"], dict):
        player["quest_log"] = {}
        return True

    return False


def listar_quests_vila(village_id):
    dados = carregar_quests(village_id)
    return dados.get("quests", {})


def obter_quest(quest_id, player=None, village_id=None):
    if village_id is None and isinstance(player, dict):
        village_id = player.get("current_location", "phandalin")

    cidades = _listar_ids_cidades()
    if village_id:
        village_id = str(village_id).strip().lower()
        cidades = [village_id] + [cidade for cidade in cidades if cidade != village_id]

    for city_id in cidades:
        quest = listar_quests_vila(city_id).get(quest_id)
        if quest:
            return city_id, quest

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
    _, quest = obter_quest(quest_id, player=player)
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

        _, quest = obter_quest(quest_id, player=player)
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
    _, quest = obter_quest(quest_id, player=player)

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
