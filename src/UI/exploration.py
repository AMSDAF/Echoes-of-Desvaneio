import random

from src.UI.combat import combater
from src.UI.utils.colors import (
    BLUE,
    CYAN,
    GREEN,
    MAGENTA,
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
from src.services.database import salvar_json
from src.services.exploration_service import (
    calcular_chance_descobrir_covil,
    garantir_estrutura_progresso,
    listar_dicas_chefe_descobertas,
    processar_exploracao,
    processar_retirada,
    tentar_acampar,
    tentar_avancar_cidade,
    tentar_descobrir_covil,
    tentar_encontrar_pista_pos_combate,
)
from src.services.quest_service import registrar_abate_quest


PLAYER_PATH = "data/core/player.json"
RARE_ENCOUNTER_CHANCE = 0.15
NOMES_ATRIBUTOS_EVENTO = {
    "strength": "Forca",
    "dexterity": "Destreza",
    "constitution": "Constituicao",
    "intelligence": "Inteligencia",
    "wisdom": "Sabedoria",
    "charisma": "Carisma",
    "luck": "Sorte",
}


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


def _formatar_recurso_atual(atual, maximo, nome, cor_padrao):
    try:
        atual = int(atual)
        maximo = int(maximo)
    except (TypeError, ValueError):
        atual = 0
        maximo = 0

    cor = RED if nome == "HP" and maximo > 0 and atual / maximo <= 0.30 else cor_padrao
    return colorir(f"{nome}: {atual}/{maximo}", cor)


def _exibir_status_expedicao(player):
    hp = _formatar_recurso_atual(player.get("current_hp", 0), player.get("max_hp", 0), "HP", GREEN)
    mana = _formatar_recurso_atual(player.get("current_mana", 0), player.get("max_mana", 0), "Mana", BLUE)
    estamina = _formatar_recurso_atual(player.get("current_stamina", 0), player.get("max_stamina", 0), "Estamina", CYAN)
    ouro = colorir(f"Ouro: {player.get('gold', 0)}G", YELLOW)
    print(f" {hp} | {mana} | {estamina} | {ouro}")


def _confirmar_combate_sem_fuga(player, titulo="CHEFE DA AREA"):
    limpar_tela()
    print(caixa_texto(titulo, cor=RED))
    _exibir_status_expedicao(player)
    print(linha_pontilhada(cor=MAGENTA))
    print(colorir("Esta luta nao permite fuga.", RED))
    print(pensamento_personagem(player.get("name", "Voce"), "Se eu entrar agora, ou ele cai... ou eu caio.", RED))
    print(linha_pontilhada(cor=MAGENTA))
    resposta = obter_entrada("Entrar mesmo assim? (S/N): ", tipo=str).strip().lower()
    return resposta == "s"


def _descricao_investigacao(progresso):
    pistas = int(progresso.get("pistas", 0))
    if pistas <= 0:
        return "Nenhum rastro confiavel."
    if pistas <= 2:
        return "Alguns indicios foram encontrados."
    if pistas <= 4:
        return "A ameaca local comeca a deixar um padrao."
    return "O covil parece cada vez mais proximo."


def _formatar_chance(chance):
    return f"{chance * 100:.1f}%"


def _exibir_dicas_chefe(player, village_id, area_id):
    dicas = listar_dicas_chefe_descobertas(player, village_id, area_id)
    if not dicas:
        print(" Dicas descobertas: Nenhuma informacao confiavel sobre o chefe ainda.")
        return

    print(" Dicas descobertas:")
    for dica in dicas:
        print(f"  - {dica.get('revealed_hint', dica.get('text', 'Dica sem texto.'))}")


def _encerrar_expedicao_por_derrota(player):
    if not player.pop("_derrota_recente", False):
        return False

    print("\n" + pensamento_personagem(player.get("name", "Voce"), "Chega de estrada por enquanto. Preciso voltar para a vila antes que o mundo termine o servico.", RED))
    aguardar_enter("\nPressione Enter para voltar para a vila...")
    return True


def _registrar_abate(player, area_id, dados_area):
    progresso = _obter_progresso_area(player, area_id)
    progresso["abates"] = progresso.get("abates", 0) + 1
    mensagens = []

    abates_necessarios = dados_area.get("required_boss_kills", 30)
    covil_revelado_agora = (
        progresso["abates"] >= abates_necessarios
        and not progresso.get("covil_descoberto", False)
        and not progresso.get("chefe_derrotado", False)
    )

    if covil_revelado_agora:
        progresso["covil_descoberto"] = True
        print(caixa_texto("COVIL DESCOBERTO", cor=YELLOW))
        print(colorir("OS RASTROS FINALMENTE SE FECHAM EM UM UNICO PONTO.", YELLOW))
        print(f"O covil do Chefe foi localizado em {dados_area['name'].upper()}!")
    else:
        pista = tentar_encontrar_pista_pos_combate(player, area_id)
        if pista.get("encontrou"):
            mensagens.append(
                pensamento_personagem(
                    player.get("name", "Voce"),
                    "No corpo, nas pegadas, no medo que ficou no ar... encontrei mais uma pista do covil.",
                    YELLOW,
                )
            )

    salvar_json(PLAYER_PATH, player)
    return mensagens


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
        mensagens_pista = _registrar_abate(player, area_id, dados_area)
        for mensagem in mensagens_pista:
            print(mensagem)
        mensagens_quest = registrar_abate_quest(player, enemy_id)
        for mensagem in mensagens_quest:
            print(colorir(mensagem, YELLOW))
        if mensagens_quest or mensagens_pista:
            aguardar_enter()
    else:
        salvar_json(PLAYER_PATH, player)

    return venceu


def _executar_combate_chefe(player, area_id, dados_area):
    boss_id = dados_area.get("boss")
    if not boss_id:
        print("\nEsta area ainda nao possui chefe configurado.")
        return False

    if not _confirmar_combate_sem_fuga(player):
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Ainda nao. Recuar antes do primeiro golpe tambem e sobreviver.", CYAN))
        aguardar_enter()
        return False

    venceu = combater(player, boss_id, pode_fugir=False)
    if venceu:
        _registrar_vitoria_chefe(player, area_id, dados_area)
        mensagens_quest = registrar_abate_quest(player, boss_id)
        for mensagem in mensagens_quest:
            print(colorir(mensagem, YELLOW))
        if mensagens_quest:
            aguardar_enter()
    else:
        salvar_json(PLAYER_PATH, player)

    return venceu


def _exibir_resultado_evento(resultado_evento, nome_hero="Voce"):
    print(caixa_texto(resultado_evento.get("title", "Evento"), cor=YELLOW))
    texto = resultado_evento.get("text")
    if texto:
        print(texto)

    check = resultado_evento.get("check")
    if check:
        nome_attr = NOMES_ATRIBUTOS_EVENTO.get(check["atributo"], check["atributo"])
        sinal = "+" if check["modificador"] >= 0 else ""
        print(
            f"Teste de {nome_attr}: d20({check['rolagem']}) "
            f"{sinal}{check['modificador']} = {check['total']} vs CD {check['dc']}"
        )
        if check["sucesso"]:
            print(pensamento_personagem(nome_hero, "Boa. Li o terreno antes dele me engolir.", GREEN))
        else:
            print(pensamento_personagem(nome_hero, "Errei a leitura. Agora o mato parece rir de mim.", RED))

    for mensagem in resultado_evento.get("messages", []):
        print(colorir(mensagem, CYAN))


def menu_interna_da_area(player, area_id, dados_area):
    nome_hero = player["name"]
    abates_necessarios = dados_area.get("required_boss_kills", 30)

    while True:
        limpar_tela()
        progresso = _obter_progresso_area(player, area_id)
        next_village_id = dados_area.get("next_village_id", "indisponivel")

        print(caixa_texto(f"ZONA DE EXPLORACAO: {dados_area['name'].upper()}", cor=GREEN))
        _exibir_status_expedicao(player)
        print(linha_pontilhada(cor=MAGENTA))
        print(f" Progresso de Abates: [{progresso.get('abates', 0)}/{abates_necessarios}]")
        print(f" Investigacao: {_descricao_investigacao(progresso)}")
        _exibir_dicas_chefe(player, player.get("current_location", "phandalin"), area_id)

        if progresso.get("chefe_derrotado", False):
            print(" Status da Area: O Guardiao desta regiao foi derrotado! [LIVRE]")
        elif progresso.get("covil_descoberto", False):
            print(" Status da Area: Voce sabe a localizacao exata do Covil do Chefe! [!]")
        else:
            print(" Status da Area: Investigando rastros do Chefe local...")

        print(linha_pontilhada(cor=MAGENTA))
        print("[1] Explorar a Area (Buscar Loot / Rolar Encontros)")
        print("[2] Montar Acampamento (Requer Kit Fogueira)")
        print("[3] Cacar Chefe da Area")
        print(f"[4] Avancar para a Proxima Cidade ({next_village_id.upper()})")
        print("[5] Bater Retirada (Voltar para a Vila Atual)")
        print(linha_pontilhada(cor=MAGENTA))

        escolha = str(obter_entrada("Qual o seu plano? ", opcoes=[1, 2, 3, 4, 5]))

        if escolha == "1":
            print(f"\n{nome_hero} avanca cautelosamente pela vegetacao densa...")
            resultado = processar_exploracao(player, area_id, dados_area)

            if resultado["evento"] == "combate":
                print("\n[EMBOSCADA!] Monstros saltam das sombras!")
                _executar_combate_area(player, area_id, dados_area, pode_fugir=True)
                if _encerrar_expedicao_por_derrota(player):
                    break

            elif resultado["evento"] == "covil_encontrado":
                print(f"\n{nome_hero} para de repente e afasta alguns galhos...")
                print(f"{nome_hero}: 'Pegadas pesadas e restos de ossos gigantes. Achei a toca do chefe!'")
                print(colorir(">>> Voce descobriu o Covil do Chefe mais cedo! <<<", YELLOW))
                aguardar_enter()

            elif resultado["evento"] == "evento_exploracao":
                _exibir_resultado_evento(resultado["resultado_evento"], nome_hero)
                if resultado.get("combate_apos_evento"):
                    print(colorir("\nA situacao vira combate!", RED))
                    aguardar_enter()
                    _executar_combate_area(player, area_id, dados_area, pode_fugir=True)
                    if _encerrar_expedicao_por_derrota(player):
                        break
                else:
                    aguardar_enter()

            elif resultado["evento"] == "seguro":
                if resultado["ouro_achado"] > 0:
                    print(f"\nA caminhada foi tranquila e voce achou um saco rasgado com {colorir(str(resultado['ouro_achado']) + 'G', YELLOW)} abandonado.")
                else:
                    print("\nVoce ronda a area, mas tudo parece deserto e silencioso por enquanto.")
                aguardar_enter()

        elif escolha == "2":
            res = tentar_acampar(player)
            if res["sucesso"]:
                print(f"\n{nome_hero} acende a fogueira. O calor do fogo acalma os nervos e fecha as feridas.")
                print(colorir(">> Vida totalmente restaurada! O Kit Fogueira foi consumido. <<", GREEN))
            else:
                print(f"\n{nome_hero} vasculha as bolsas frustrado: 'Droga... sem um Kit Fogueira eu nao vou durar a noite nesse frio.'")
            aguardar_enter()

        elif escolha == "3":
            progresso = _obter_progresso_area(player, area_id)

            if progresso.get("chefe_derrotado", False):
                print(f"\n{nome_hero}: 'O monstro ja esta morto. Nao ha mais nada para cacar aqui.'")
                aguardar_enter()
            elif progresso.get("abates", 0) >= abates_necessarios or progresso.get("covil_descoberto", False):
                print(f"\n{nome_hero} marcha em direcao ao perigo fatal...")
                _executar_combate_chefe(player, area_id, dados_area)
                if _encerrar_expedicao_por_derrota(player):
                    break
                aguardar_enter()
            else:
                chance = calcular_chance_descobrir_covil(progresso)
                print(caixa_texto("CACADA AO COVIL", cor=YELLOW))
                print(f"Chance de encontrar rastros decisivos: {colorir(_formatar_chance(chance), YELLOW)}")
                print(pensamento_personagem(nome_hero, "Vou seguir os rastros. Se eu estiver certo, encontro a toca. Se estiver errado, so perco tempo e folego.", CYAN))
                resultado_busca = tentar_descobrir_covil(player, area_id)
                if resultado_busca.get("sucesso"):
                    print("\n" + caixa_texto("COVIL DESCOBERTO", cor=YELLOW))
                    print(pensamento_personagem(nome_hero, "As marcas se alinham. Pegadas, sangue seco, silencio demais... achei.", GREEN))
                    print(colorir(f"O covil do Chefe foi localizado em {dados_area['name'].upper()}!", YELLOW))
                    aguardar_enter("\nPressione Enter para decidir se encara o perigo...")
                    _executar_combate_chefe(player, area_id, dados_area)
                    if _encerrar_expedicao_por_derrota(player):
                        break
                else:
                    print("\n" + pensamento_personagem(nome_hero, "Nada. Os rastros quebram antes de virar caminho. Preciso de mais pistas ou mais corpos no chao.", RED))
                aguardar_enter()

        elif escolha == "4":
            res = tentar_avancar_cidade(player, area_id, dados_area)
            if res["status"] == "sucesso_transicao":
                print(f"\n{nome_hero} segue viagem pela estrada agora segura, deixando a area para tras...")
                print(colorir(f">> Bem-vindo a {res['nova_vila'].upper()}! <<", GREEN))
                aguardar_enter("\nPressione Enter para entrar na nova cidade...")
                break
            elif res["status"] == "sem_proxima_cidade":
                print(f"\n{nome_hero}: 'Essa trilha nao parece levar a uma nova cidade. Melhor escolher outro caminho.'")
                aguardar_enter()
            else:
                print(caixa_texto("BARREIRA CRUCIAL", cor=RED))
                print(colorir("O Guardiao da Estrada bloqueia a passagem!", RED))
                print(f"{nome_hero}: 'Ele bloqueou a estrada... vou ter que lutar. E fugir nao parece uma opcao.'")
                venceu = _executar_combate_chefe(player, area_id, dados_area)
                if _encerrar_expedicao_por_derrota(player):
                    break
                if venceu:
                    print("\nCom o Guardiao derrotado, tente avancar novamente para seguir viagem.")
                aguardar_enter()

        elif escolha == "5":
            res = processar_retirada(player, dados_area)
            if res["evento"] == "combate":
                print("\nNo caminho de volta para a vila, algo ouviu seus passos!")
                _executar_combate_area(player, area_id, dados_area, pode_fugir=True)
                if _encerrar_expedicao_por_derrota(player):
                    break
            else:
                print(f"\n{nome_hero} consegue voltar pelas trilhas em seguranca ate os portoes da vila.")
            break

        else:
            print(f"\n{nome_hero}: 'Preciso escolher um plano que faca sentido.'")
