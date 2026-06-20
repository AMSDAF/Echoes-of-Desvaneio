import random

from src.UI.combat import combater
from src.services.database import salvar_json
from src.services.exploration_service import (
    garantir_estrutura_progresso,
    processar_exploracao,
    processar_retirada,
    tentar_acampar,
    tentar_avancar_cidade,
)


PLAYER_PATH = "data/core/player.json"
RARE_ENCOUNTER_CHANCE = 0.15


def _obter_progresso_area(player, area_id):
    garantir_estrutura_progresso(player, area_id)
    return player["progresso_areas"][area_id]


def _sortear_enemy_id(dados_area):
    """Sorteia um inimigo normal ou raro da area atual."""
    normal_enemies = dados_area.get("normal_enemies", [])
    rare_enemies = dados_area.get("rare_enemies", [])

    if rare_enemies and (not normal_enemies or random.random() <= RARE_ENCOUNTER_CHANCE):
        return random.choice(rare_enemies)

    if normal_enemies:
        return random.choice(normal_enemies)

    if rare_enemies:
        return random.choice(rare_enemies)

    return None


def _registrar_abate(player, area_id, dados_area):
    progresso = _obter_progresso_area(player, area_id)
    progresso["abates"] = progresso.get("abates", 0) + 1

    abates_necessarios = dados_area.get("required_boss_kills", 30)
    covil_revelado_agora = (
        progresso["abates"] >= abates_necessarios
        and not progresso.get("covil_descoberto", False)
        and not progresso.get("chefe_derrotado", False)
    )

    if covil_revelado_agora:
        progresso["covil_descoberto"] = True
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("OS RASTROS FINALMENTE SE FECHAM EM UM UNICO PONTO.")
        print(f"O covil do Chefe foi localizado em {dados_area['name'].upper()}!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    salvar_json(PLAYER_PATH, player)


def _registrar_vitoria_chefe(player, area_id, dados_area):
    progresso = _obter_progresso_area(player, area_id)
    progresso["chefe_derrotado"] = True
    progresso["covil_descoberto"] = True

    if dados_area.get("boss_unlocks_next_village", False):
        next_village_id = dados_area.get("next_village_id")
        if next_village_id:
            player.setdefault("unlocked_villages", {})[next_village_id] = True
            print("\nA estrada antes bloqueada agora esta aberta.")
            print(f">> Nova vila liberada: {next_village_id.upper()} <<")

    salvar_json(PLAYER_PATH, player)


def _executar_combate_area(player, area_id, dados_area, pode_fugir=True):
    enemy_id = _sortear_enemy_id(dados_area)
    if not enemy_id:
        print("\nNada respondeu aos seus passos. Esta area nao possui inimigos configurados.")
        return False

    venceu = combater(player, enemy_id, pode_fugir=pode_fugir)
    if venceu:
        _registrar_abate(player, area_id, dados_area)
    else:
        salvar_json(PLAYER_PATH, player)

    return venceu


def _executar_combate_chefe(player, area_id, dados_area):
    boss_id = dados_area.get("boss")
    if not boss_id:
        print("\nEsta area ainda nao possui chefe configurado.")
        return False

    venceu = combater(player, boss_id, pode_fugir=False)
    if venceu:
        _registrar_vitoria_chefe(player, area_id, dados_area)
    else:
        salvar_json(PLAYER_PATH, player)

    return venceu


def menu_interna_da_area(player, area_id, dados_area):
    nome_hero = player["name"]
    abates_necessarios = dados_area.get("required_boss_kills", 30)

    while True:
        progresso = _obter_progresso_area(player, area_id)
        next_village_id = dados_area.get("next_village_id", "indisponivel")

        print("\n==============================================")
        print(f"        ZONA DE EXPLORACAO: {dados_area['name'].upper()}        ")
        print("==============================================")
        print(f" Progresso de Abates: [{progresso.get('abates', 0)}/{abates_necessarios}]")

        if progresso.get("chefe_derrotado", False):
            print(" Status da Area: O Guardiao desta regiao foi derrotado! [LIVRE]")
        elif progresso.get("covil_descoberto", False):
            print(" Status da Area: Voce sabe a localizacao exata do Covil do Chefe! [!]")
        else:
            print(" Status da Area: Investigando rastros do Chefe local...")

        print("----------------------------------------------")
        print("[1] Explorar a Area (Buscar Loot / Rolar Encontros)")
        print("[2] Montar Acampamento (Requer Kit Fogueira)")
        print("[3] Cacar Chefe da Area")
        print(f"[4] Avancar para a Proxima Cidade ({next_village_id.upper()})")
        print("[5] Bater Retirada (Voltar para a Vila Atual)")
        print("==============================================")

        escolha = input("Qual o seu plano? ").strip()

        if escolha == "1":
            print(f"\n{nome_hero} avanca cautelosamente pela vegetacao densa...")
            resultado = processar_exploracao(player, area_id, dados_area)

            if resultado["evento"] == "combate":
                print("\n[EMBOSCADA!] Monstros saltam das sombras!")
                _executar_combate_area(player, area_id, dados_area, pode_fugir=True)

            elif resultado["evento"] == "covil_encontrado":
                print(f"\n{nome_hero} para de repente e afasta alguns galhos...")
                print(f"{nome_hero}: 'Pegadas pesadas e restos de ossos gigantes. Achei a toca do chefe!'")
                print(">>> Voce descobriu o Covil do Chefe mais cedo! <<<")
                input("\nPressione Enter para continuar...")

            elif resultado["evento"] == "seguro":
                if resultado["ouro_achado"] > 0:
                    print(f"\nA caminhada foi tranquila e voce achou um saco rasgado com {resultado['ouro_achado']}G abandonado.")
                else:
                    print("\nVoce ronda a area, mas tudo parece deserto e silencioso por enquanto.")
                input("\nPressione Enter para continuar...")

        elif escolha == "2":
            res = tentar_acampar(player)
            if res["sucesso"]:
                print(f"\n{nome_hero} acende a fogueira. O calor do fogo acalma os nervos e fecha as feridas.")
                print(">> Vida totalmente restaurada! O Kit Fogueira foi consumido. <<")
            else:
                print(f"\n{nome_hero} vasculha as bolsas frustrado: 'Droga... sem um Kit Fogueira eu nao vou durar a noite nesse frio.'")
            input("\nPressione Enter para continuar...")

        elif escolha == "3":
            progresso = _obter_progresso_area(player, area_id)

            if progresso.get("chefe_derrotado", False):
                print(f"\n{nome_hero}: 'O monstro ja esta morto. Nao ha mais nada para cacar aqui.'")
                input("\nPressione Enter para continuar...")
            elif progresso.get("abates", 0) >= abates_necessarios or progresso.get("covil_descoberto", False):
                print(f"\n{nome_hero} marcha em direcao ao perigo fatal...")
                _executar_combate_chefe(player, area_id, dados_area)
                input("\nPressione Enter para continuar...")
            else:
                print(f"\n{nome_hero}: 'O chefe esta bem escondido. Preciso eliminar mais dos seus capangas primeiro ou dar a sorte de achar seu covil.'")
                input("\nPressione Enter para continuar...")

        elif escolha == "4":
            res = tentar_avancar_cidade(player, area_id, dados_area)
            if res["status"] == "sucesso_transicao":
                print(f"\n{nome_hero} segue viagem pela estrada agora segura, deixando a area para tras...")
                print(f">> Bem-vindo a {res['nova_vila'].upper()}! <<")
                input("\nPressione Enter para entrar na nova cidade...")
                break
            elif res["status"] == "sem_proxima_cidade":
                print(f"\n{nome_hero}: 'Essa trilha nao parece levar a uma nova cidade. Melhor escolher outro caminho.'")
                input("\nPressione Enter para continuar...")
            else:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("BARREIRA CRUCIAL! O Guardiao da Estrada bloqueia a passagem!")
                print(f"{nome_hero}: 'Ele bloqueou a estrada... vou ter que lutar. E fugir nao parece uma opcao.'")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                venceu = _executar_combate_chefe(player, area_id, dados_area)
                if venceu:
                    print("\nCom o Guardiao derrotado, tente avancar novamente para seguir viagem.")
                input("\nPressione Enter para continuar...")

        elif escolha == "5":
            res = processar_retirada(player, dados_area)
            if res["evento"] == "combate":
                print("\nNo caminho de volta para a vila, algo ouviu seus passos!")
                _executar_combate_area(player, area_id, dados_area, pode_fugir=True)
            else:
                print(f"\n{nome_hero} consegue voltar pelas trilhas em seguranca ate os portoes da vila.")
            break

        else:
            print(f"\n{nome_hero}: 'Preciso escolher um plano que faca sentido.'")
