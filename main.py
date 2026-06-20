from src.UI.character_creation import criar_personagem
from src.UI.bestiary import exibir_bestiario
from src.UI.exploration import menu_interna_da_area
from src.UI.inventory import exibir_status_e_inventario
from src.UI.npcs import exibir_npcs_vila
from src.UI.quests import exibir_quadro_missoes
from src.UI.shop import visitar_comercio
from src.UI.tavern import exibir_taverna
from src.UI.utils.colors import (
    CYAN,
    GREEN,
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
from src.services.database import carregar_json, salvar_json
from src.services.bestiary_service import garantir_bestiario
from src.services.level_service import garantir_estrutura_evolucao
from src.services.npc_service import garantir_memoria_npcs
from src.services.quest_service import garantir_quest_log


player = carregar_json("data/core/player.json")

if not player:
    player = criar_personagem()
    garantir_quest_log(player)
    garantir_memoria_npcs(player)
    garantir_bestiario(player)
    salvar_json("data/core/player.json", player)
else:
    modificado = garantir_estrutura_evolucao(player)
    modificado = garantir_quest_log(player) or modificado
    modificado = garantir_memoria_npcs(player) or modificado
    modificado = garantir_bestiario(player) or modificado
    if modificado:
        salvar_json("data/core/player.json", player)


def menu_principal(player):
    while True:
        limpar_tela()
        print(caixa_texto("MENU PRINCIPAL", cor=CYAN))
        print(f"Nome: {player['name']} | Classe: {player['class']} | Nivel: {player['level']}")
        print(f"Ouro: {colorir(str(player['gold']) + 'G', YELLOW)} | XP: {player['xp']}")
        print(linha_pontilhada())
        print("[1] Explorar Regioes Selvagens")
        print("[2] Visitar o Centro Comercial")
        print("[3] Ir para a Taverna")
        print("[4] Conversar com Moradores")
        print("[5] Quadro de Missoes")
        print("[6] Bestiario")
        print("[7] Ver Status e Inventario")
        print("[8] Salvar e Sair")
        print(linha_pontilhada())

        opcao = str(obter_entrada("Escolha uma opcao: ", opcoes=[1, 2, 3, 4, 5, 6, 7, 8]))

        if opcao == "1":
            dados_exploracao = carregar_json("data/core/exploration.json")
            local_atual_id = player.get("current_location", "phandalin")

            if local_atual_id not in dados_exploracao:
                local_atual_id = "phandalin"

            dados_da_vila = dados_exploracao[local_atual_id]
            areas_disponiveis = dados_da_vila.get("areas", {})

            limpar_tela()
            print(caixa_texto(f"MAPA DE EXPLORACAO: {dados_exploracao[local_atual_id]['display_name'].upper()}", cor=GREEN))
            lista_areas = list(areas_disponiveis.items())

            for i, (_, area_info) in enumerate(lista_areas, 1):
                status = "[BLOQUEADO]" if not area_info.get("unlocked", True) else ""
                print(f"[{i}] {area_info['name']} {status}")

            print(f"[{len(lista_areas) + 1}] Voltar para a Vila")
            print(linha_pontilhada())

            escolha_area = obter_entrada(
                "Escolha uma area para marchar: ",
                opcoes=list(range(1, len(lista_areas) + 2)),
            ) - 1
            if escolha_area == len(lista_areas):
                continue

            id_area_sel, dados_area_sel = lista_areas[escolha_area]

            if not dados_area_sel.get("unlocked", True):
                print(colorir(f"\n{player['name']}: 'Essa regiao parece perigosa demais ou inacessivel por caminhos normais ainda...'", RED))
                aguardar_enter()
                continue

            print(f"\nMarchando rumo a {dados_area_sel['name']}...")
            aguardar_enter()
            menu_interna_da_area(player, id_area_sel, dados_area_sel)

        elif opcao == "2":
            print("\n" + pensamento_personagem(player["name"], "Vamos ver quanto custa sobreviver hoje.", YELLOW))
            visitar_comercio(player)

        elif opcao == "3":
            print("\n" + pensamento_personagem(player["name"], "Uma caneca, um rumor e talvez uma cama. Nessa ordem.", YELLOW))
            exibir_taverna(player)

        elif opcao == "4":
            print("\n" + pensamento_personagem(player["name"], "Se a vila tem segredos, alguem aqui ja deixou escapar metade.", CYAN))
            exibir_npcs_vila(player)

        elif opcao == "5":
            print("\n" + pensamento_personagem(player["name"], "Vamos ver quais problemas tem preco hoje.", YELLOW))
            exibir_quadro_missoes(player)

        elif opcao == "6":
            print("\n" + pensamento_personagem(player["name"], "Melhor aprender com cicatrizes antigas antes de ganhar novas.", CYAN))
            exibir_bestiario(player)

        elif opcao == "7":
            print("\n" + pensamento_personagem(player["name"], "Hora de conferir se ainda sou eu por baixo da poeira.", CYAN))
            exibir_status_e_inventario(player)

        elif opcao == "8":
            salvar_json("data/core/player.json", player)
            print(pensamento_personagem(player["name"], "Tudo anotado. Se eu sumir, ao menos a historia sabe onde parei.", GREEN))
            break
        else:
            print(pensamento_personagem(player["name"], "Isso nao e um plano. Preciso escolher direito.", RED))


menu_principal(player)
