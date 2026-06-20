from src.services.exploration_service import (
    garantir_estrutura_progresso,
    processar_exploracao,
    processar_retirada,
    tentar_acampar,
    tentar_avancar_cidade,
)


def menu_interna_da_area(player, area_id, dados_area):
    nome_hero = player["name"]
    abates_necessarios = dados_area.get("required_boss_kills", 30)

    while True:
        garantir_estrutura_progresso(player, area_id)
        progresso = player["progresso_areas"][area_id]
        next_village_id = dados_area.get("next_village_id", "indisponivel")

        print("\n==============================================")
        print(f"        ZONA DE EXPLORACAO: {dados_area['name'].upper()}        ")
        print("==============================================")
        print(f" Progresso de Abates: [{progresso['abates']}/{abates_necessarios}]")

        if progresso["chefe_derrotado"]:
            print(" Status da Area: O Guardiao desta regiao foi derrotado! [LIVRE]")
        elif progresso["covil_descoberto"]:
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
                print("\n[EMBOSCADA!] Monstros saltam das sombras! [GATILHO DE COMBATE NORMAL]")
                input("\nPressione Enter para simular fim da luta...")

            elif resultado["evento"] == "covil_encontrado":
                print(f"\n{nome_hero} para de repente e afasta alguns galhos...")
                print(f"{nome_hero}: 'Caramba... pegadas pesadas e restos de ossos gigantes. Achei a toca do desgracado!'")
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
            if progresso["chefe_derrotado"]:
                print(f"\n{nome_hero}: 'O monstro ja esta morto. Nao ha mais nada para cacar aqui.'")
            elif progresso["abates"] >= abates_necessarios or progresso["covil_descoberto"]:
                print(f"\n{nome_hero} marcha em direcao ao perigo fatal...")
                print(f"[GATILHO DE COMBATE: BOSS CONTRA {dados_area['boss'].upper()}!]")
                input("\nPressione Enter para simular vitoria no Boss...")
                progresso["chefe_derrotado"] = True
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
                print(f"{nome_hero}: 'Ele bloqueou a estrada... vou ter que lutar. E sinto que se eu tentar correr no meio da briga, ele me pega pelas costas!'")
                print(f"[GATILHO: Iniciando combate contra {dados_area['boss'].upper()} com a opcao 'Fugir' desativada!]")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                input("\nPressione Enter para encarar o seu destino...")

        elif escolha == "5":
            res = processar_retirada(player, dados_area)
            if res["evento"] == "combate":
                print("\nNo caminho de volta para a vila, algo ouviu seus passos! [EMBOSCADA DE RETIRADA]")
                input("\nPressione Enter para lutar e fugir para a cidade...")
            else:
                print(f"\n{nome_hero} consegue voltar pelas trilhas em seguranca ate os portoes da vila.")
            break

        else:
            print(f"\n{nome_hero}: 'Preciso escolher um plano que faca sentido.'")
