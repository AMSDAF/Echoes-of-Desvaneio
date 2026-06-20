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
    for i, class_key in enumerate(class_options, 1):
        classe = classes[class_key]
        print(f"[{i}] {classe['name']} - {classe['description']}")

    while True:
        try:
            choice = int(input("Escolha o numero da sua classe: ")) - 1
            if 0 <= choice < len(class_options):
                selected_class_key = class_options[choice]
                return classes[selected_class_key]
            print("Opcao invalida!")
        except ValueError:
            print("Por favor, digite um numero valido.")


def _escolher_raca(racas):
    race_options = list(racas.keys())
    for i, race_key in enumerate(race_options, 1):
        raca = racas[race_key]
        bonus_texto = _formatar_bonus_racial(raca)
        passiva_texto = _formatar_passiva_racial(raca)
        print(f"[{i}] {raca['name']} - {raca['description']}")
        print(f"    Bonus: {bonus_texto}")
        print(f"    Passiva: {passiva_texto}")

    while True:
        try:
            choice = int(input("Escolha o numero da sua raca: ")) - 1
            if 0 <= choice < len(race_options):
                selected_race_key = race_options[choice]
                return racas[selected_race_key]
            print("Opcao invalida!")
        except ValueError:
            print("Por favor, digite um numero valido.")


def criar_personagem():
    classes = obter_classes_disponiveis()
    racas = obter_racas_disponiveis()

    print("====================================================")
    print("Saudacoes, viajante! Para dar inicio a sua lendaria jornada,")
    print("primeiro me diga: qual e o seu nome?")
    print("====================================================")
    name = input(">> ").strip()

    print(f"\nBelo nome, {name}! Dentro deste mundo, existem varios caminhos")
    print("a se seguir. Qual sera a sua vocacao?")
    selected_class = _escolher_classe(classes)

    print(f"\nExcelente. Agora escolha a origem do sangue e da historia de {name}:")
    selected_race = _escolher_raca(racas)

    print(f"\n{name}, {selected_race['name']} e grande {selected_class['name']}! Vejo grande potencial.")
    print("Que tal dar um upgrade em seus atributos?")
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
        print(f"\nPontos restantes: {points_to_distribute}")
        print("Atributos atuais antes do bonus racial:")
        for attr, value in player_attributes.items():
            print(f"- {NOMES_ATRIBUTOS.get(attr, attr.capitalize())}: {value}")

        print("\nQual atributo deseja aumentar?")
        print("[1] Forca | [2] Destreza | [3] Constituicao | [4] Inteligencia")
        print("[5] Sabedoria | [6] Carisma | [7] Sorte")
        attr_choice = input(">> ").strip()

        if attr_choice in attr_map:
            chosen_attr = attr_map[attr_choice]
            try:
                nome_attr = NOMES_ATRIBUTOS.get(chosen_attr, chosen_attr.capitalize())
                pts = int(input(f"Quantos pontos colocar em {nome_attr}? "))
                sucesso, pontos_restantes = validar_distribuicao_pontos(
                    player_attributes[chosen_attr], pts, points_to_distribute
                )
                if sucesso:
                    player_attributes[chosen_attr] += pts
                    points_to_distribute = pontos_restantes
                else:
                    print("Quantidade de pontos invalida!")
            except ValueError:
                print("Por favor, digite um numero valido.")
        else:
            print("Opcao invalida!")

    print("\n====================================================")
    print("Otima combinacao! Chegou a hora de se equipar.")
    print("Tome esses 250 de ouro e va na loja para comprar seus equipamentos.")
    print("Se cuide, viajante, e ate breve...")
    print("====================================================")
    input("\nPressione Enter para continuar...")

    return construir_personagem_inicial(name, selected_class, selected_race, player_attributes)
