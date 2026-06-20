from src.services.database import carregar_json, salvar_json
from src.UI.character_creation import criar_personagem
from src.UI.exploration import menu_interna_da_area
from src.UI.inventory import exibir_status_e_inventario
from src.UI.shop import visitar_comercio


player = carregar_json("data/core/player.json")

if not player:
    player = criar_personagem()
    salvar_json("data/core/player.json", player)


def menu_principal(player):
    while True:
        print("\n=== MENU PRINCIPAL ===")
        print(f"Nome: {player['name']} | Classe: {player['class']} | Nivel: {player['level']}")
        print(f"Ouro: {player['gold']}G | XP: {player['xp']}")
        print("=======================")
        print("[1] Explorar Regioes Selvagens")
        print("[2] Visitar o Centro Comercial")
        print("[3] Ver Status e Inventario")
        print("[4] Salvar e Sair")
        print("=======================")

        opcao = input("Escolha uma opcao: ").strip()

        if opcao == "1":
            dados_exploracao = carregar_json("data/core/exploration.json")
            local_atual_id = player.get("current_location", "phandalin")

            if local_atual_id not in dados_exploracao:
                local_atual_id = "phandalin"

            dados_da_vila = dados_exploracao[local_atual_id]
            areas_disponiveis = dados_da_vila.get("areas", {})

            print(f"\n--- MAPA DE EXPLORACAO: {dados_exploracao[local_atual_id]['display_name'].upper()} ---")
            lista_areas = list(areas_disponiveis.items())

            for i, (_, area_info) in enumerate(lista_areas, 1):
                status = "[BLOQUEADO]" if not area_info.get("unlocked", True) else ""
                print(f"[{i}] {area_info['name']} {status}")

            print(f"[{len(lista_areas) + 1}] Voltar para a Vila")
            print("---------------------------------------")

            try:
                escolha_area = int(input("Escolha uma area para marchar: ")) - 1
                if escolha_area == len(lista_areas):
                    continue

                if 0 <= escolha_area < len(lista_areas):
                    id_area_sel, dados_area_sel = lista_areas[escolha_area]

                    if not dados_area_sel.get("unlocked", True):
                        print(f"\n{player['name']}: 'Essa regiao parece perigosa demais ou inacessivel por caminhos normais ainda...'")
                        input("\nPressione Enter para continuar...")
                        continue

                    print(f"\nMarchando rumo a {dados_area_sel['name']}...")
                    menu_interna_da_area(player, id_area_sel, dados_area_sel)
                else:
                    print("\nOpcao invalida!")
            except ValueError:
                print("\nPor favor, digite um numero valido.")

        elif opcao == "2":
            print("\nEntrando no Centro Comercial...")
            visitar_comercio(player)

        elif opcao == "3":
            print("\nExibindo ficha de personagem...")
            exibir_status_e_inventario(player)

        elif opcao == "4":
            salvar_json("data/core/player.json", player)
            print("\nProgresso salvo com sucesso! Ate logo, viajante.")
            break
        else:
            print("\nOpcao invalida!")


menu_principal(player)
