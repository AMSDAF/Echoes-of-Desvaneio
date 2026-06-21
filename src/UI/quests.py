from src.UI.utils.colors import (
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    aguardar_enter,
    caixa_texto,
    colorir,
    linha_pontilhada,
    limpar_tela,
    obter_entrada,
    pensamento_personagem,
)
from src.UI.level_up import exibir_tela_level_up
from src.services.quest_service import (
    STATUS_ACTIVE,
    STATUS_CLAIMED,
    STATUS_COMPLETED,
    aceitar_quest,
    carregar_quests,
    entregar_quest,
    formatar_progresso_quest,
    garantir_quest_log,
    listar_quests_vila,
    obter_estado_quest,
)


def _nome_status(status):
    nomes = {
        STATUS_ACTIVE: colorir("ativa", CYAN),
        STATUS_COMPLETED: colorir("concluida", GREEN),
        STATUS_CLAIMED: colorir("recompensa recebida", MAGENTA),
    }
    return nomes.get(status, "disponivel")


def _exibir_resumo_quest(quest, estado=None):
    print(colorir(quest["title"], YELLOW))
    print(f"Solicitante: {quest.get('giver', 'Desconhecido')}")
    print(quest.get("description", "Sem descricao."))
    if estado:
        print(f"Status: {_nome_status(estado.get('status'))}")

    for linha in formatar_progresso_quest(quest, estado):
        print(f"- {linha}")

    rewards = quest.get("rewards", {})
    print(
        f"Recompensa: {colorir(str(rewards.get('gold', 0)) + 'G', YELLOW)} | "
        f"{rewards.get('xp', 0)} XP"
    )


def _listar_disponiveis(player, village_id):
    quests = listar_quests_vila(village_id)
    disponiveis = [
        (quest_id, quest)
        for quest_id, quest in quests.items()
        if not obter_estado_quest(player, quest_id) and not quest.get("hidden", False)
    ]

    if not disponiveis:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Nada novo no quadro. Ou os problemas acabaram, ou ficaram bons em se esconder.", CYAN))
        aguardar_enter()
        return

    while True:
        limpar_tela()
        print(caixa_texto("MISSOES DISPONIVEIS", cor=YELLOW))
        for i, (_, quest) in enumerate(disponiveis, 1):
            print(f"[{i}] {quest['title']} - {quest.get('giver', 'Desconhecido')}")
        print(f"[{len(disponiveis) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha uma missao para ler: ",
            opcoes=list(range(1, len(disponiveis) + 2)),
        ) - 1

        if escolha == len(disponiveis):
            return

        quest_id, quest = disponiveis[escolha]
        limpar_tela()
        print(caixa_texto("DETALHES DA MISSAO", cor=YELLOW))
        _exibir_resumo_quest(quest)
        print(linha_pontilhada())
        aceitar = obter_entrada("Aceitar esta missao? (S/N): ", tipo=str).strip().lower()
        if aceitar == "s":
            resultado = aceitar_quest(player, quest_id)
            cor = GREEN if resultado.get("sucesso") else RED
            print(pensamento_personagem(player.get("name", "Voce"), resultado["mensagem"], cor))
            aguardar_enter()
            return


def _listar_ativas(player):
    garantir_quest_log(player)
    ativas = []
    for quest_id, estado in player.get("quest_log", {}).items():
        if estado.get("status") not in {STATUS_ACTIVE, STATUS_COMPLETED}:
            continue

        _, quest = _obter_quest_local(quest_id)
        if quest:
            ativas.append((quest_id, quest, estado))

    if not ativas:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Meu diario esta limpo. Estranho... quase confortavel.", CYAN))
        aguardar_enter()
        return

    limpar_tela()
    print(caixa_texto("DIARIO DE MISSOES", cor=CYAN))
    for _, quest, estado in ativas:
        _exibir_resumo_quest(quest, estado)
        print(linha_pontilhada())
    aguardar_enter()


def _obter_quest_local(quest_id):
    for village_data in carregar_quests().values():
        quest = village_data.get("quests", {}).get(quest_id)
        if quest:
            return village_data, quest

    return None, None


def _entregar_concluidas(player):
    garantir_quest_log(player)
    concluidas = []
    for quest_id, estado in player.get("quest_log", {}).items():
        if estado.get("status") != STATUS_COMPLETED:
            continue

        _, quest = _obter_quest_local(quest_id)
        if quest:
            concluidas.append((quest_id, quest))

    if not concluidas:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Ainda nao tenho nada pronto para cobrar. Melhor terminar o servico antes.", CYAN))
        aguardar_enter()
        return

    while True:
        limpar_tela()
        print(caixa_texto("ENTREGAR MISSOES", cor=GREEN))
        for i, (_, quest) in enumerate(concluidas, 1):
            print(f"[{i}] {quest['title']}")
        print(f"[{len(concluidas) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha uma missao para entregar: ",
            opcoes=list(range(1, len(concluidas) + 2)),
        ) - 1

        if escolha == len(concluidas):
            return

        quest_id, _ = concluidas[escolha]
        resultado = entregar_quest(player, quest_id)
        if resultado.get("sucesso"):
            print(pensamento_personagem(player.get("name", "Voce"), f"Servico feito: {resultado['title']}. Agora vem a parte boa.", GREEN))
            print(pensamento_personagem(player.get("name", "Voce"), f"No bolso: {resultado['gold']}G. Na pele: {resultado['xp']} XP de experiencia.", YELLOW))
            resultado_xp = resultado.get("resultado_xp") or {}
            if resultado_xp.get("levels_ganhos", 0) > 0:
                aguardar_enter("\nPressione Enter para sentir a experiencia assentar...")
                exibir_tela_level_up(player, resultado_xp)
                return
        else:
            print(pensamento_personagem(player.get("name", "Voce"), resultado.get("mensagem", "Nao consigo entregar isso ainda."), RED))

        aguardar_enter()
        return


def exibir_quadro_missoes(player):
    garantir_quest_log(player)
    village_id = player.get("current_location", "phandalin")
    village_data = carregar_quests().get(village_id, carregar_quests().get("phandalin", {}))
    titulo = village_data.get("display_name", "Quadro de Missoes")

    while True:
        limpar_tela()
        print(caixa_texto(titulo.upper(), cor=YELLOW))
        print("[1] Ver missoes disponiveis")
        print("[2] Ver diario de missoes")
        print("[3] Entregar missoes concluidas")
        print("[4] Voltar")
        print(linha_pontilhada())

        escolha = str(obter_entrada("Escolha uma opcao: ", opcoes=[1, 2, 3, 4]))
        if escolha == "1":
            _listar_disponiveis(player, village_id)
        elif escolha == "2":
            _listar_ativas(player)
        elif escolha == "3":
            _entregar_concluidas(player)
        elif escolha == "4":
            return
