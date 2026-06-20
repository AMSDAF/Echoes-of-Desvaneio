from src.services.character_service import (
    obter_classes_disponiveis, validar_distribuicao_pontos, construir_personagem_inicial
)

def criar_personagem():
    classes = obter_classes_disponiveis()
    
    print("====================================================")
    print("Saudações, viajante! Para dar início à sua lendária jornada,")
    print("primeiro me diga: qual é o seu nome?")
    print("====================================================")
    name = input(">> ").strip()
    
    print(f"\nBelo nome, {name}! Dentro deste mundo, existem vários caminhos")
    print("a se seguir. Qual será a sua vocação?")
    
    class_options = list(classes.keys())
    for i, class_key in enumerate(class_options, 1):
        print(f"[{i}] {classes[class_key]['name']} - {classes[class_key]['description']}")
        
    while True:
        try:
            choice = int(input("Escolha o número da sua classe: ")) - 1
            if 0 <= choice < len(class_options):
                selected_class_key = class_options[choice]
                selected_class = classes[selected_class_key]
                break
            print("Opção inválida!")
        except ValueError:
            print("Por favor, digite um número válido.")
    
    print(f"\n{name}, um grande {selected_class['name']}! Vejo grande potencial.")
    print("Que tal dar um upgrade em seus atributos?")
    print("Dica: Strength (Guerreiro), Agility (Arqueiro), Intelligence (Mago), Vitality (Vida!)")
    
    player_attributes = dict(selected_class['base_attributes'])
    points_to_distribute = 6
    
    attr_map = {"1": "strength", "2": "agility", "3": "intelligence", "4": "vitality"}
    
    while points_to_distribute > 0:
        print(f"\nPontos restantes: {points_to_distribute}")
        print("Atributos atuais:")
        for attr, value in player_attributes.items():
            print(f"- {attr.capitalize()}: {value}")
            
        print("\nQual atributo deseja aumentar?")
        print("[1] Strength | [2] Agility | [3] Intelligence | [4] Vitality")
        attr_choice = input(">> ").strip()
        
        if attr_choice in attr_map:
            chosen_attr = attr_map[attr_choice]
            try:
                pts = int(input(f"Quantos pontos colocar em {chosen_attr.capitalize()}? "))
                sucesso, pontos_restantes = validar_distribuicao_pontos(
                    player_attributes[chosen_attr], pts, points_to_distribute
                )
                if sucesso:
                    player_attributes[chosen_attr] += pts
                    points_to_distribute = pontos_restantes
                else:
                    print("Quantidade de pontos inválida!")
            except ValueError:
                print("Por favor, digite um número válido.")
        else:
            print("Opção inválida!")

    print("\n====================================================")
    print("Ótima combinação! Chegou a hora de se equipar.")
    print("Tome esses 250 de ouro e vá na loja para comprar seus equipamentos.")
    print("Se cuide, viajante, e até breve...")
    print("====================================================")
    input("\nPressione Enter para continuar...")

    return construir_personagem_inicial(name, selected_class, player_attributes)