from src.UI.utils.colors import (
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    aguardar_enter,
    caixa_texto,
    colorir,
    fala_entidade,
    linha_pontilhada,
    limpar_tela,
    obter_entrada,
    pensamento_personagem,
)
from src.services.npc_service import (
    carregar_npcs,
    listar_npcs_vila,
    listar_quests_npc,
    listar_topicos_npc,
    obter_memoria_npc,
    obter_rumor_npc,
    obter_saudacao,
    obter_texto_topico,
    registrar_conversa,
    tentar_aceitar_quest_npc,
)
from src.services.quest_service import STATUS_ACTIVE, STATUS_CLAIMED, STATUS_COMPLETED


NOMES_LOCAL = {
    "tavern": "Taverna",
    "market": "Mercado",
    "road": "Estrada",
    "temple": "Templo",
}


def _status_quest(estado):
    if not estado:
        return colorir("disponivel", YELLOW)
    if estado.get("status") == STATUS_ACTIVE:
        return colorir("em andamento", CYAN)
    if estado.get("status") == STATUS_COMPLETED:
        return colorir("concluida", GREEN)
    if estado.get("status") == STATUS_CLAIMED:
        return colorir("recompensa recebida", MAGENTA)

    return estado.get("status", "desconhecido")


def _exibir_ficha_npc(npc, memoria):
    print(caixa_texto(npc.get("name", "NPC").upper(), cor=CYAN))
    print(colorir(npc.get("title", "Morador"), YELLOW))
    print(f"Local: {NOMES_LOCAL.get(npc.get('location'), npc.get('location', 'vila'))}")
    print(f"Disposicao: {npc.get('disposition', 'neutro')}")
    print(f"Conversas: {memoria.get('talk_count', 0)} | Afinidade: {memoria.get('affinity', 0)}")
    print(linha_pontilhada())
    print(npc.get("description", "Alguem que ainda nao contou sua historia."))


def _conversar_topicos(player, npc_id, npc):
    topicos = listar_topicos_npc(npc)
    if not topicos:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Nao consigo arrancar mais nada desse assunto agora.", CYAN))
        aguardar_enter()
        return

    while True:
        limpar_tela()
        print(caixa_texto(f"ASSUNTOS COM {npc.get('name', 'NPC').upper()}", cor=MAGENTA))
        for i, (_, texto) in enumerate(topicos, 1):
            print(f"[{i}] {texto[:55]}...")
        print(f"[{len(topicos) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha um assunto: ",
            opcoes=list(range(1, len(topicos) + 2)),
        ) - 1

        if escolha == len(topicos):
            return

        topic_id, texto = topicos[escolha]
        registrar_conversa(player, npc_id, topic_id)
        print(caixa_texto(npc.get("name", "NPC"), cor=YELLOW))
        print(f"\"{texto}\"")
        aguardar_enter()


def _pedir_trabalho(player, npc):
    quests = listar_quests_npc(player, npc)
    if not quests:
        print("\n" + fala_entidade(npc.get("name", "NPC"), "Nao tenho nenhum pedido pessoal para voce agora. Mas volte vivo. Isso sempre abre portas."))
        aguardar_enter()
        return

    while True:
        limpar_tela()
        print(caixa_texto(f"TRABALHOS DE {npc.get('name', 'NPC').upper()}", cor=YELLOW))
        for i, (_, quest, estado) in enumerate(quests, 1):
            print(f"[{i}] {quest['title']} - {_status_quest(estado)}")
            print(f"    {quest.get('description', '')}")
        print(f"[{len(quests) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha uma missao: ",
            opcoes=list(range(1, len(quests) + 2)),
        ) - 1

        if escolha == len(quests):
            return

        quest_id, quest, estado = quests[escolha]
        if estado:
            print("\n" + fala_entidade(npc.get("name", "NPC"), f"Voce ja sabe o que precisa fazer sobre {quest['title']}."))
            aguardar_enter()
            continue

        resultado = tentar_aceitar_quest_npc(player, quest_id)
        cor = GREEN if resultado.get("sucesso") else RED
        print(pensamento_personagem(player.get("name", "Voce"), resultado.get("mensagem", "Nada muda. Por enquanto."), cor))
        aguardar_enter()
        quests = listar_quests_npc(player, npc)


def _menu_npc(player, npc_id, npc):
    while True:
        limpar_tela()
        memoria = obter_memoria_npc(player, npc_id)
        _exibir_ficha_npc(npc, memoria)
        print(linha_pontilhada(cor=MAGENTA))
        print("[1] Cumprimentar")
        print("[2] Conversar sobre assuntos")
        print("[3] Pedir rumores")
        print("[4] Perguntar sobre pedidos pessoais")
        print("[5] Voltar")
        print(linha_pontilhada(cor=MAGENTA))

        escolha = str(obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3, 4, 5]))

        if escolha == "1":
            memoria = registrar_conversa(player, npc_id)
            print(f"\n{npc.get('name', 'NPC')}: \"{obter_saudacao(npc, memoria)}\"")
            aguardar_enter()
        elif escolha == "2":
            _conversar_topicos(player, npc_id, npc)
        elif escolha == "3":
            registrar_conversa(player, npc_id, "rumor")
            print(f"\n{npc.get('name', 'NPC')} baixa a voz: \"{obter_rumor_npc(npc)}\"")
            aguardar_enter()
        elif escolha == "4":
            registrar_conversa(player, npc_id, "personal_request")
            _pedir_trabalho(player, npc)
        elif escolha == "5":
            return


def exibir_npcs_vila(player):
    village_id = player.get("current_location", "phandalin")
    dados_vila = carregar_npcs().get(village_id, carregar_npcs().get("phandalin", {}))
    npcs = listar_npcs_vila(village_id) or listar_npcs_vila("phandalin")
    nome_vila = dados_vila.get("display_name", "Moradores")

    while True:
        limpar_tela()
        print(caixa_texto(nome_vila.upper(), cor=CYAN))
        if not npcs:
            print(pensamento_personagem(player.get("name", "Voce"), "Nao conheco ninguem importante por aqui ainda.", CYAN))
            aguardar_enter()
            return

        lista_npcs = list(npcs.items())
        for i, (_, npc) in enumerate(lista_npcs, 1):
            local = NOMES_LOCAL.get(npc.get("location"), npc.get("location", "vila"))
            print(f"[{i}] {npc['name']} - {npc.get('title', 'Morador')} ({local})")
        print(f"[{len(lista_npcs) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Com quem deseja falar? ",
            opcoes=list(range(1, len(lista_npcs) + 2)),
        ) - 1

        if escolha == len(lista_npcs):
            return

        npc_id, npc = lista_npcs[escolha]
        _menu_npc(player, npc_id, npc)
