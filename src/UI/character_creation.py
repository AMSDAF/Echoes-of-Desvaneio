from src.UI.utils.colors import (
    CYAN,
    GREEN,
    MAGENTA,
    YELLOW,
    aguardar_enter,
    caixa_texto,
    colorir,
    fala_entidade,
    linha_pontilhada,
    obter_entrada,
    pensamento_personagem,
)
from src.services.attribute_service import NOMES_ATRIBUTOS, normalizar_atributos
from src.services.character_service import (
    construir_personagem_inicial,
    obter_classes_disponiveis,
    obter_racas_disponiveis,
    validar_distribuicao_pontos,
)


def _formatar_bonus_racial(raca_dados):
    bonus = raca_dados.get("attribute_bonuses", {})
    if not bonus:
        return "sem bonus"

    partes = []
    for attr, valor in bonus.items():
        nome_attr = NOMES_ATRIBUTOS.get(attr, attr.capitalize())
        sinal = "+" if valor >= 0 else ""
        partes.append(f"{nome_attr} {sinal}{valor}")

    return ", ".join(partes)


def _formatar_passiva_racial(raca_dados):
    passiva = raca_dados.get("passive", {})
    if not passiva:
        return "sem passiva"

    nome = passiva.get("name", "Passiva")
    descricao = passiva.get("description", "")
    if descricao:
        return f"{nome}: {descricao}"

    return nome


def _escolher_classe(classes):
    class_options = list(classes.keys())
    print(caixa_texto("ESCOLHA SUA CLASSE", cor=CYAN))
    for i, class_key in enumerate(class_options, 1):
        classe = classes[class_key]
        print(f"[{i}] {classe['name']} - {classe['description']}")

    choice = obter_entrada(
        "Escolha o numero da sua classe: ",
        opcoes=list(range(1, len(class_options) + 1)),
    ) - 1
    selected_class_key = class_options[choice]
    return classes[selected_class_key]


def _escolher_raca(racas):
    race_options = list(racas.keys())
    print(caixa_texto("ESCOLHA SUA RACA", cor=MAGENTA))
    for i, race_key in enumerate(race_options, 1):
        raca = racas[race_key]
        bonus_texto = _formatar_bonus_racial(raca)
        passiva_texto = _formatar_passiva_racial(raca)
        print(f"[{i}] {raca['name']} - {raca['description']}")
        print(f"    Bonus: {bonus_texto}")
        print(f"    Passiva: {passiva_texto}")

    choice = obter_entrada(
        "Escolha o numero da sua raca: ",
        opcoes=list(range(1, len(race_options) + 1)),
    ) - 1
    selected_race_key = race_options[choice]
    return racas[selected_race_key]


def criar_personagem():
    classes = obter_classes_disponiveis()
    racas = obter_racas_disponiveis()

    print(caixa_texto("ECHOES OF DESVANEIO", cor=YELLOW))
    print(fala_entidade("Voz no Desvaneio", "Antes da estrada lembrar seus passos, ela precisa lembrar seu nome."))
    print(linha_pontilhada())
    name = obter_entrada(">> ", tipo=str).strip()
    while not name:
        print(fala_entidade("Voz no Desvaneio", "Um nome vazio nao ecoa. Tente de novo.", MAGENTA))
        name = obter_entrada(">> ", tipo=str).strip()

    print("\n" + fala_entidade("Voz no Desvaneio", f"{name}. Sim... esse nome cabe em uma historia perigosa. Qual sera sua vocacao?"))
    selected_class = _escolher_classe(classes)

    print("\n" + fala_entidade("Voz no Desvaneio", "Agora escolha a origem do sangue, da memoria e das cicatrizes que ainda virao:"))
    selected_race = _escolher_raca(racas)

    print("\n" + pensamento_personagem(name, f"{selected_race['name']} e {selected_class['name']}. E isso precisa significar alguma coisa.", GREEN))
    print(fala_entidade("Voz no Desvaneio", "Distribua seus pontos. A estrada cobra caro por fraquezas ignoradas."))
    print("Dica: Forca (fisico), Destreza (defesa/fuga), Constituicao (vida), Inteligencia (magia), Sorte (drops).")
    print(f"Bonus racial escolhido: {_formatar_bonus_racial(selected_race)}")
    print(f"Passiva racial: {_formatar_passiva_racial(selected_race)}")

    player_attributes = normalizar_atributos(selected_class["base_attributes"])
    points_to_distribute = 10

    attr_map = {
        "1": "strength",
        "2": "dexterity",
        "3": "constitution",
        "4": "intelligence",
        "5": "wisdom",
        "6": "charisma",
        "7": "luck",
    }

    while points_to_distribute > 0:
        print(caixa_texto(f"PONTOS RESTANTES: {points_to_distribute}", cor=GREEN))
        print("Atributos atuais antes do bonus racial:")
        for attr, value in player_attributes.items():
            print(f"- {NOMES_ATRIBUTOS.get(attr, attr.capitalize())}: {value}")

        print("\nQual atributo deseja aumentar?")
        print("[1] Forca | [2] Destreza | [3] Constituicao | [4] Inteligencia")
        print("[5] Sabedoria | [6] Carisma | [7] Sorte")
        attr_choice = str(obter_entrada(">> ", opcoes=[1, 2, 3, 4, 5, 6, 7]))

        if attr_choice in attr_map:
            chosen_attr = attr_map[attr_choice]
            nome_attr = NOMES_ATRIBUTOS.get(chosen_attr, chosen_attr.capitalize())
            pts = obter_entrada(f"Quantos pontos colocar em {nome_attr}? ")
            sucesso, pontos_restantes = validar_distribuicao_pontos(
                player_attributes[chosen_attr], pts, points_to_distribute
            )
            if sucesso:
                player_attributes[chosen_attr] += pts
                points_to_distribute = pontos_restantes
            else:
                print(pensamento_personagem(name, "Nao. Forcar alem do que tenho agora so vai quebrar o plano.", RED))
        else:
            print(pensamento_personagem(name, "Esse caminho nao existe. Preciso escolher outro.", RED))

    print(caixa_texto("PERSONAGEM CRIADO", cor=GREEN))
    print(pensamento_personagem(name, "Estou pronto o bastante para comecar. O resto eu aprendo sobrevivendo.", GREEN))
    print(fala_entidade("Voz no Desvaneio", "Pegue este ouro inicial. Equipamento ruim transforma coragem em obituario."))
    print(linha_pontilhada())
    aguardar_enter()

    return construir_personagem_inicial(name, selected_class, selected_race, player_attributes)
