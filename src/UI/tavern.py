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
from src.services.city_data_service import carregar_taverna_cidade
from src.services.database import salvar_json
from src.services.event_service import resolver_evento_urbano


PLAYER_PATH = "data/core/player.json"
REST_OPTIONS = {
    1: {
        "name": "Cochilo Curto",
        "duration": "1 hora",
        "cost": 2,
        "restore": {"hp": 0.0, "mana": 0.25, "stamina": 0.35},
        "start": "Uma hora nao fecha corte nenhum... mas talvez cale o tremor das maos.",
        "end": "Nao foi descanso de verdade, mas minha respiracao voltou ao lugar.",
        "art": ["             Zzz...", "       O barulho da taverna vira uma parede distante."],
    },
    2: {
        "name": "Quarto Simples",
        "duration": "4 horas",
        "cost": 5,
        "restore": {"hp": 0.25, "mana": 0.60, "stamina": 0.75},
        "start": "Quatro horas. Se eu fechar os olhos rapido, talvez o corpo aceite continuar.",
        "end": "Nao acordei inteiro... mas acordei capaz.",
        "art": ["             Zzz...", "          Zzz... Zzz...", "     As dores diminuem enquanto a tarde escorre pela janela."],
    },
    3: {
        "name": "Noite Inteira",
        "duration": "8 horas",
        "cost": 10,
        "restore": {"hp": 1.0, "mana": 1.0, "stamina": 1.0},
        "start": "Uma noite inteira. Hoje eu escolho viver ate amanha.",
        "end": "Pela primeira vez em dias, acordei sem sentir o mundo mordendo meus ossos.",
        "art": ["             Zzz...", "          Zzz... Zzz...", "       A noite passa. O mundo fica quieto.", "     A manha encontra voce respirando melhor."],
    },
}
REST_KEYS = {
    1: "short",
    2: "simple",
    3: "full",
}
NOMES_ATRIBUTOS_EVENTO = {
    "strength": "Forca",
    "dexterity": "Destreza",
    "constitution": "Constituicao",
    "intelligence": "Inteligencia",
    "wisdom": "Sabedoria",
    "charisma": "Carisma",
    "luck": "Sorte",
}


def _obter_cidade_atual(player):
    return player.get("current_location", "phandalin")


def _obter_dados_taverna(player):
    local_atual = _obter_cidade_atual(player)
    return carregar_taverna_cidade(local_atual)


def _obter_custo_descanso(dados_taverna, rest_key, fallback):
    try:
        custo = dados_taverna.get("services", {}).get("rest_costs", {}).get(rest_key, fallback)
        return max(0, int(custo))
    except (AttributeError, TypeError, ValueError):
        return max(0, int(fallback))


def _obter_config_rumor(dados_taverna):
    try:
        config = dados_taverna.get("services", {}).get("rumor", {})
        custo = max(0, int(config.get("cost", 0)))
        limite_bruto = config.get("limit")
        limite = None if limite_bruto is None else max(0, int(limite_bruto))
        return {"cost": custo, "limit": limite}
    except (AttributeError, TypeError, ValueError):
        return {"cost": 0, "limit": None}


def _pode_ouvir_rumor(player, cidade, limite):
    usados = player.setdefault("tavern_rumors_used", {})
    if not isinstance(usados, dict):
        player["tavern_rumors_used"] = {}
        usados = player["tavern_rumors_used"]

    quantidade = max(0, int(usados.get(cidade, 0)))
    return limite is None or quantidade < limite


def _ouvir_boato(player, dados_taverna, cidade):
    boatos = dados_taverna.get("rumors", [])
    if not boatos:
        print("\n" + pensamento_personagem("Voce", "Muito barulho, pouca informacao. Hoje a taverna so sabe beber.", CYAN))
        return False

    config = _obter_config_rumor(dados_taverna)
    custo = config["cost"]
    limite = config["limit"]
    nome_heroi = player.get("name", "Voce")

    if not _pode_ouvir_rumor(player, cidade, limite):
        print("\n" + pensamento_personagem(nome_heroi, "Ja ouvi tudo que esta taverna pretende vender hoje.", RED))
        return False

    if player.get("gold", 0) < custo:
        print("\n" + pensamento_personagem(nome_heroi, "Informacao tambem custa moeda. Minha bolsa nao acompanha minha curiosidade.", RED))
        return False

    player["gold"] = max(0, int(player.get("gold", 0)) - custo)
    usados = player.setdefault("tavern_rumors_used", {})
    usados[cidade] = max(0, int(usados.get(cidade, 0))) + 1
    salvar_json(PLAYER_PATH, player)

    print(f"\nUma voz na mesa ao lado murmura: \"{random.choice(boatos)}\"")
    if custo > 0:
        print(pensamento_personagem(nome_heroi, f"A informacao me custou {custo}G. Restam {player.get('gold', 0)}G.", YELLOW))
    return True


def _conversar_taverneiro(dados_taverna):
    taverneiro = dados_taverna.get("keeper", "Taverneiro")
    dialogos = dados_taverna.get("dialogues", [])

    if not dialogos:
        print("\n" + fala_entidade(taverneiro, "Sem novidades hoje. Beba algo e mantenha os olhos abertos."))
        return

    print("\n" + fala_entidade(taverneiro, random.choice(dialogos)))


def _formatar_recurso(atual, maximo, nome, cor):
    return colorir(f"{nome}: {atual}/{maximo}", cor)


def _restaurar_percentual(player, resource, percentual):
    current_key = f"current_{resource}"
    max_key = f"max_{resource}"
    maximo = int(player.get(max_key, player.get(current_key, 0)))
    atual = int(player.get(current_key, maximo))

    if percentual >= 1:
        restaurado = maximo - atual
        player[current_key] = maximo
        return max(0, restaurado)

    restaurado = int(round(maximo * percentual))
    novo_valor = min(maximo, atual + restaurado)
    player[current_key] = novo_valor
    return max(0, novo_valor - atual)


def _exibir_status_descanso(player):
    hp = _formatar_recurso(player.get("current_hp", 0), player.get("max_hp", 0), "HP", GREEN)
    mana = _formatar_recurso(player.get("current_mana", 0), player.get("max_mana", 0), "Mana", BLUE)
    estamina = _formatar_recurso(player.get("current_stamina", 0), player.get("max_stamina", 0), "Estamina", CYAN)
    ouro = colorir(f"Ouro: {player.get('gold', 0)}G", YELLOW)
    print(f"{hp} | {mana} | {estamina} | {ouro}")


def _aplicar_descanso(player, opcao_descanso):
    restore = opcao_descanso["restore"]
    return {
        "hp": _restaurar_percentual(player, "hp", restore.get("hp", 0)),
        "mana": _restaurar_percentual(player, "mana", restore.get("mana", 0)),
        "stamina": _restaurar_percentual(player, "stamina", restore.get("stamina", 0)),
    }


def _descansar_na_estalagem(player, dados_taverna):
    taverneiro = dados_taverna.get("keeper", "Taverneiro")

    limpar_tela()
    print(caixa_texto("ALUGAR UM QUARTO", cor=BLUE))
    _exibir_status_descanso(player)
    print(linha_pontilhada())
    for indice, opcao in REST_OPTIONS.items():
        custo = _obter_custo_descanso(dados_taverna, REST_KEYS[indice], opcao["cost"])
        print(
            f"[{indice}] {opcao['name']} - {opcao['duration']} - "
            f"{colorir(str(custo) + 'G', YELLOW)}"
        )
        print(
            f"    HP +{int(opcao['restore']['hp'] * 100)}% | "
            f"Mana +{int(opcao['restore']['mana'] * 100)}% | "
            f"Estamina +{int(opcao['restore']['stamina'] * 100)}%"
        )
    print("[4] Voltar")
    print(linha_pontilhada())

    escolha = obter_entrada("Quanto tempo pretende dormir? ", opcoes=[1, 2, 3, 4])
    if escolha == 4:
        return

    opcao_descanso = REST_OPTIONS[escolha]
    custo = _obter_custo_descanso(
        dados_taverna,
        REST_KEYS[escolha],
        opcao_descanso["cost"],
    )
    nome_heroi = player.get("name", "Voce")

    if player.get("gold", 0) < custo:
        print(colorir(f"\n{taverneiro}: \"Quarto quente custa moeda quente. Nao trabalho de graca, viajante.\"", RED))
        print(pensamento_personagem(nome_heroi, "Sem moeda, sem cama. A estrada vai rir de mim se eu insistir.", RED))
        return

    print("\n" + pensamento_personagem(nome_heroi, opcao_descanso["start"], CYAN))
    player["gold"] -= custo
    recuperado = _aplicar_descanso(player, opcao_descanso)
    salvar_json(PLAYER_PATH, player)

    print(caixa_texto(f"{opcao_descanso['duration'].upper()} DE DESCANSO", cor=BLUE))
    for linha in opcao_descanso["art"]:
        print(linha)
    print(linha_pontilhada())
    print(pensamento_personagem(nome_heroi, opcao_descanso["end"], GREEN))
    print(
        pensamento_personagem(
            nome_heroi,
            (
                f"Recuperei {recuperado['hp']} de vida, "
                f"{recuperado['mana']} de mana e {recuperado['stamina']} de estamina. "
                f"Restam {player.get('gold', 0)}G."
            ),
            YELLOW,
        )
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
    cidade_atual = _obter_cidade_atual(player)
    if not dados_taverna:
        limpar_tela()
        print(caixa_texto("TAVERNA INDISPONIVEL", cor=YELLOW))
        print(
            pensamento_personagem(
                player.get("name", "Viajante"),
                "Nao encontro uma estalagem aberta nesta cidade.",
                CYAN,
            )
        )
        aguardar_enter()
        return

    nome_taverna = dados_taverna.get("name", "Taverna Local")
    nome_heroi = player.get("name", "Viajante")

    while True:
        limpar_tela()
        print(caixa_texto(nome_taverna.upper(), cor=YELLOW))
        print(f"{nome_heroi} sente o cheiro de madeira velha, ensopado quente e historias mal contadas.")
        print(f"Ouro: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}")
        print(linha_pontilhada(cor=MAGENTA))
        config_rumor = _obter_config_rumor(dados_taverna)
        usados = max(0, int(player.get("tavern_rumors_used", {}).get(cidade_atual, 0))) if isinstance(player.get("tavern_rumors_used", {}), dict) else 0
        limite_texto = "sem limite" if config_rumor["limit"] is None else f"{usados}/{config_rumor['limit']}"
        print(f"[1] Ouvir boatos locais - {config_rumor['cost']}G ({limite_texto})")
        print("[2] Conversar com o Taverneiro")
        print("[3] Alugar um Quarto para Descansar")
        print("[4] Observar a Taverna")
        print("[5] Voltar para a Vila")
        print(linha_pontilhada(cor=MAGENTA))

        escolha = str(obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3, 4, 5]))

        if escolha == "1":
            _ouvir_boato(player, dados_taverna, cidade_atual)
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
