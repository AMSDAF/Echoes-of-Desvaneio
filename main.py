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
from src.services.city_data_service import carregar_exploracao_cidade
from src.services.level_service import garantir_estrutura_evolucao
from src.services.level_service import xp_para_proximo_level
from src.services.npc_service import garantir_memoria_npcs
from src.services.quest_service import garantir_quest_log


def garantir_vilas_desbloqueadas(player):
    if not isinstance(player.get("unlocked_villages"), dict):
        player["unlocked_villages"] = {}

    modificado = False
    vilas = player["unlocked_villages"]

    if vilas.get("oakridge") is not True:
        vilas["oakridge"] = True
        modificado = True

    local_atual = player.get("current_location")
    if not local_atual:
        local_atual = "phandalin"
        player["current_location"] = local_atual
        modificado = True

    if vilas.get(local_atual) is not True:
        vilas[local_atual] = True
        modificado = True

    return modificado


def obter_vilas_liberadas(player):
    vilas = player.setdefault("unlocked_villages", {})
    local_atual = player.get("current_location", "phandalin")
    vilas[local_atual] = True
    vilas["oakridge"] = True

    liberadas = []
    for village_id, desbloqueada in vilas.items():
        if not desbloqueada:
            continue

        dados_vila = carregar_exploracao_cidade(village_id)
        if dados_vila:
            liberadas.append((village_id, dados_vila.get("display_name", village_id.title())))

    return liberadas


def viajar_entre_vilas(player):
    vilas_liberadas = obter_vilas_liberadas(player)
    local_atual = player.get("current_location", "phandalin")

    limpar_tela()
    print(caixa_texto("VIAGEM ENTRE VILAS", cor=CYAN))
    print(pensamento_personagem(player["name"], "A estrada aberta tambem e uma escolha. Melhor decidir para onde meus passos apontam.", CYAN))
    print(linha_pontilhada())

    for indice, (village_id, nome_vila) in enumerate(vilas_liberadas, 1):
        marcador = " [ATUAL]" if village_id == local_atual else ""
        print(f"[{indice}] {nome_vila}{marcador}")
    print(f"[{len(vilas_liberadas) + 1}] Voltar")
    print(linha_pontilhada())

    escolha = obter_entrada(
        "Escolha o destino: ",
        opcoes=list(range(1, len(vilas_liberadas) + 2)),
    )

    if escolha == len(vilas_liberadas) + 1:
        return

    destino_id, destino_nome = vilas_liberadas[escolha - 1]
    if destino_id == local_atual:
        print(pensamento_personagem(player["name"], "Ja estou aqui. As vezes o mapa tambem tira sarro.", YELLOW))
        aguardar_enter()
        return

    player["current_location"] = destino_id
    salvar_json("data/core/player.json", player)
    print(colorir(f"\n>> Voce viajou para {destino_nome}. <<", GREEN))
    print(pensamento_personagem(player["name"], "Outra placa, outro cheiro de estrada. Ainda sou eu chegando vivo.", GREEN))
    aguardar_enter()


player = carregar_json("data/core/player.json")

if not player:
    player = criar_personagem()
    garantir_quest_log(player)
    garantir_memoria_npcs(player)
    garantir_bestiario(player)
    garantir_vilas_desbloqueadas(player)
    salvar_json("data/core/player.json", player)
else:
    modificado = garantir_estrutura_evolucao(player)
    modificado = garantir_quest_log(player) or modificado
    modificado = garantir_memoria_npcs(player) or modificado
    modificado = garantir_bestiario(player) or modificado
    modificado = garantir_vilas_desbloqueadas(player) or modificado
    if modificado:
        salvar_json("data/core/player.json", player)


def menu_principal(player):
    while True:
        limpar_tela()
        print(caixa_texto("MENU PRINCIPAL", cor=CYAN))
        print(f"Nome: {player['name']} | Classe: {player['class']} | Nivel: {player['level']}")
        print(
            f"Ouro: {colorir(str(player['gold']) + 'G', YELLOW)} | "
            f"XP: {player['xp']}/{xp_para_proximo_level(player.get('level', 1))} | "
            f"Vila: {player.get('current_location', 'phandalin').upper()}"
        )
        print(linha_pontilhada())
        print("[1] Explorar Regioes Selvagens")
        print("[2] Visitar o Centro Comercial")
        print("[3] Ir para a Taverna")
        print("[4] Conversar com Moradores")
        print("[5] Quadro de Missoes")
        print("[6] Bestiario")
        print("[7] Ver Status e Inventario")
        print("[8] Viajar entre Vilas")
        print("[9] Salvar e Sair")
        print(linha_pontilhada())

        opcao = str(obter_entrada("Escolha uma opcao: ", opcoes=[1, 2, 3, 4, 5, 6, 7, 8, 9]))

        if opcao == "1":
            local_atual_id = player.get("current_location", "phandalin")
            dados_da_vila = carregar_exploracao_cidade(local_atual_id)

            if not dados_da_vila:
                print(
                    "\n"
                    + pensamento_personagem(
                        player["name"],
                        "Nao encontro um mapa confiavel desta regiao. Melhor nao partir as cegas.",
                        RED,
                    )
                )
                aguardar_enter()
                continue

            areas_disponiveis = dados_da_vila.get("areas", {})

            if not areas_disponiveis:
                print(
                    "\n"
                    + pensamento_personagem(
                        player["name"],
                        "Nao ha rotas de exploracao registradas por aqui.",
                        YELLOW,
                    )
                )
                aguardar_enter()
                continue

            limpar_tela()
            nome_vila = dados_da_vila.get("display_name", local_atual_id).upper()
            print(caixa_texto(f"MAPA DE EXPLORACAO: {nome_vila}", cor=GREEN))
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
            viajar_entre_vilas(player)

        elif opcao == "9":
            salvar_json("data/core/player.json", player)
            print(pensamento_personagem(player["name"], "Tudo anotado. Se eu sumir, ao menos a historia sabe onde parei.", GREEN))
            break
        else:
            print(pensamento_personagem(player["name"], "Isso nao e um plano. Preciso escolher direito.", RED))


menu_principal(player)
