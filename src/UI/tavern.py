import random

from src.UI.utils.colors import (
    BLUE,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    caixa_texto,
    colorir,
    fala_entidade,
    linha_pontilhada,
    aguardar_enter,
    limpar_tela,
    obter_entrada,
    pensamento_personagem,
)
from src.services.database import carregar_json, salvar_json
from src.services.event_service import resolver_evento_urbano


PLAYER_PATH = "data/core/player.json"
TAVERN_PATH = "data/core/tavern.json"
REST_COST = 10
NOMES_ATRIBUTOS_EVENTO = {
    "strength": "Forca",
    "dexterity": "Destreza",
    "constitution": "Constituicao",
    "intelligence": "Inteligencia",
    "wisdom": "Sabedoria",
    "charisma": "Carisma",
    "luck": "Sorte",
}


def _obter_dados_taverna(player):
    tavernas = carregar_json(TAVERN_PATH) or {}
    local_atual = player.get("current_location", "phandalin")
    return tavernas.get(local_atual) or tavernas.get("phandalin") or {}


def _ouvir_boato(dados_taverna):
    boatos = dados_taverna.get("rumors", [])
    if not boatos:
        print("\n" + pensamento_personagem("Voce", "Muito barulho, pouca informacao. Hoje a taverna so sabe beber.", CYAN))
        return

    print(f"\nUma voz na mesa ao lado murmura: \"{random.choice(boatos)}\"")


def _conversar_taverneiro(dados_taverna):
    taverneiro = dados_taverna.get("keeper", "Taverneiro")
    dialogos = dados_taverna.get("dialogues", [])

    if not dialogos:
        print("\n" + fala_entidade(taverneiro, "Sem novidades hoje. Beba algo e mantenha os olhos abertos."))
        return

    print("\n" + fala_entidade(taverneiro, random.choice(dialogos)))


def _descansar_na_estalagem(player, dados_taverna):
    taverneiro = dados_taverna.get("keeper", "Taverneiro")

    if player.get("gold", 0) < REST_COST:
        print(colorir(f"\n{taverneiro}: \"Quarto quente custa moeda quente. Nao trabalho de graca, viajante.\"", RED))
        return

    player["gold"] -= REST_COST
    player["current_hp"] = player.get("max_hp", player.get("current_hp", 100))
    player["current_mana"] = player.get("max_mana", player.get("current_mana", 50))
    player["current_stamina"] = player.get("max_stamina", player.get("current_stamina", 50))
    salvar_json(PLAYER_PATH, player)

    print(caixa_texto("A NOITE PASSA DEVAGAR...", cor=BLUE))
    print("             Zzz...")
    print("          Zzz... Zzz...")
    print("     O mundo fica quieto por algumas horas.")
    print(linha_pontilhada())
    print(colorir("Voce acorda se sentindo totalmente revigorado!", GREEN))
    print(
        f"{colorir('HP', GREEN)}, {colorir('Mana', BLUE)} e "
        f"{colorir('Estamina', CYAN)} restaurados. "
        f"Ouro restante: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}"
    )


def _exibir_evento_taverna(player):
    resultado = resolver_evento_urbano(player, "tavern")
    if not resultado:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Estranho. Ate os copos parecem evitar barulho agora.", CYAN))
        return

    print(caixa_texto(resultado.get("title", "Evento"), cor=MAGENTA))
    if resultado.get("text"):
        print(resultado["text"])

    check = resultado.get("check")
    if check:
        nome_attr = NOMES_ATRIBUTOS_EVENTO.get(check["atributo"], check["atributo"])
        sinal = "+" if check["modificador"] >= 0 else ""
        print(
            f"Teste de {nome_attr}: d20({check['rolagem']}) "
            f"{sinal}{check['modificador']} = {check['total']} vs CD {check['dc']}"
        )
        if check["sucesso"]:
            print(pensamento_personagem(player.get("name", "Voce"), "Peguei o fio certo dessa conversa.", GREEN))
        else:
            print(pensamento_personagem(player.get("name", "Voce"), "Perdi alguma coisa no meio do ruido.", RED))

    for mensagem in resultado.get("messages", []):
        print(colorir(mensagem, CYAN))


def exibir_taverna(player):
    dados_taverna = _obter_dados_taverna(player)
    nome_taverna = dados_taverna.get("name", "Taverna Local")
    nome_heroi = player.get("name", "Viajante")

    while True:
        limpar_tela()
        print(caixa_texto(nome_taverna.upper(), cor=YELLOW))
        print(f"{nome_heroi} sente o cheiro de madeira velha, ensopado quente e historias mal contadas.")
        print(f"Ouro: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}")
        print(linha_pontilhada(cor=MAGENTA))
        print("[1] Ouvir boatos locais")
        print("[2] Conversar com o Taverneiro")
        print(f"[3] Alugar um Quarto para Descansar (Custo: {colorir(str(REST_COST) + 'G', YELLOW)})")
        print("[4] Observar a Taverna")
        print("[5] Voltar para a Vila")
        print(linha_pontilhada(cor=MAGENTA))

        escolha = str(obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3, 4, 5]))

        if escolha == "1":
            _ouvir_boato(dados_taverna)
            aguardar_enter()
        elif escolha == "2":
            _conversar_taverneiro(dados_taverna)
            aguardar_enter()
        elif escolha == "3":
            _descansar_na_estalagem(player, dados_taverna)
            aguardar_enter()
        elif escolha == "4":
            _exibir_evento_taverna(player)
            aguardar_enter()
        elif escolha == "5":
            print("\n" + pensamento_personagem(nome_heroi, "Chega de calor e rumor. A rua me chama de volta.", CYAN))
            break
        else:
            print(f"\n{nome_heroi}: 'Melhor escolher algo que o taverneiro entenda.'")
