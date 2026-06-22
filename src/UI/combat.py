import random

from src.UI.utils.colors import (
    BLUE,
    BOLD,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    YELLOW,
    caixa_texto,
    colorir,
    pensamento_personagem,
    linha_pontilhada,
    aguardar_enter,
    limpar_tela,
    obter_entrada,
)
from src.UI.level_up import exibir_tela_level_up
from src.services.attribute_service import formatar_percentual
from src.services.bestiary_service import registrar_derrota_inimigo, registrar_encontro
from src.services.combat_service import (
    calcular_chance_contra_ataque,
    calcular_chance_esquiva,
    calcular_chance_fuga,
    calcular_chance_critico,
    calcular_chance_sorte_esquiva,
    calcular_custo_habilidade,
    calcular_dano_habilidade,
    calcular_desgaste_arma,
    calcular_percentual_dano_bloqueio,
    carregar_dados_monstro,
    escalar_monstro_para_level,
    jogador_tem_recurso_para_habilidade,
    listar_habilidades_conhecidas,
    obter_efeitos_raciais,
    preparar_uso_habilidade,
    processar_defesa,
    processar_vitoria,
)
from src.services.condition_service import (
    aplicar_reducao_dano_por_condicoes,
    calcular_bonus_critico_condicoes,
    calcular_penalidade_reacao_condicoes,
    entidade_tem_condicao,
    processar_condicoes_inicio_turno,
    tentar_aplicar_condicao,
)
from src.services.database import salvar_json
from src.services.item_service import (
    aplicar_desgaste_defensivo,
    calcular_atributos_totais,
    calcular_propriedades_equipadas,
    consumir_consumivel,
    item_e_consumivel,
    obter_quantidade_item,
    obter_bonus_resistencia_condicao,
    obter_condicoes_ao_acertar,
)
from src.services.level_service import garantir_estrutura_evolucao


def _formatar_hp(atual, maximo):
    cor = RED if maximo and atual / maximo <= 0.25 else GREEN
    return colorir(f"{atual}/{maximo} HP", cor)


def _formatar_mana(atual, maximo):
    return colorir(f"{atual}/{maximo} Mana", BLUE)


def _formatar_estamina(atual, maximo):
    return colorir(f"{atual}/{maximo} Estamina", CYAN)


def _formatar_ouro(valor):
    return colorir(f"{valor}G", YELLOW)


def _cor_recurso(resource):
    cores = {
        "hp": GREEN,
        "mana": BLUE,
        "stamina": CYAN,
    }
    return cores.get(resource, MAGENTA)


def _exibir_resultado_consumivel(player, resultado):
    nome_heroi = player.get("name", "Voce")
    nome_item = resultado.get("item_name", "Consumivel")
    cor = GREEN
    linhas = []

    if "resource" in resultado:
        cor = _cor_recurso(resultado["resource"])
        linhas.append(f"{resultado.get('resource_name', 'Recurso')}: +{resultado.get('restored', 0)}")
    elif "condition_removed" in resultado:
        cor = GREEN
        linhas.append(f"Removeu: {resultado.get('condition_name', 'condicao')}")
    elif "condition_applied" in resultado:
        cor = MAGENTA
        linhas.append(
            f"Aplicou: {resultado.get('condition_name', 'condicao')} "
            f"por {resultado.get('duration', 1)} turno(s)"
        )
    else:
        cor = RED
        linhas.append("Nenhum efeito perceptivel.")

    limpar_tela()
    print(caixa_texto("EFEITO DO ITEM", cor=cor))
    print(f"Item usado: {colorir(nome_item, YELLOW)}")
    print(linha_pontilhada(cor=MAGENTA))
    for linha in linhas:
        print(colorir(linha, cor))
    print(linha_pontilhada(cor=MAGENTA))
    print(f"Vida: {_formatar_hp(player.get('current_hp', 0), player.get('max_hp', 0))}")
    print(f"Mana: {_formatar_mana(player.get('current_mana', 0), player.get('max_mana', 0))}")
    print(f"Estamina: {_formatar_estamina(player.get('current_stamina', 0), player.get('max_stamina', 0))}")
    print(linha_pontilhada(cor=MAGENTA))
    print(pensamento_personagem(nome_heroi, "Uma garrafa a menos. Uma chance a mais.", cor))


def _fala_inimigo(dados_monstro, momento, nome_monstro=None):
    linhas = dados_monstro.get("battle_lines", {}).get(momento, [])
    if not linhas:
        return

    nome = nome_monstro or dados_monstro.get("name", "Inimigo")
    print(colorir(f"{nome}: \"{random.choice(linhas)}\"", MAGENTA))


def _exibir_ataque_critico(atacante_nome, alvo_nome, atacante_e_player=True):
    print("\n" + caixa_texto("ATAQUE CRITICO", cor=YELLOW))
    if atacante_e_player:
        falas = [
            "Esse golpe entrou limpo demais para ter sido sorte.",
            "Agora sim. Senti a abertura quebrar por dentro.",
            "Foi certeiro. O tipo de golpe que muda a luta.",
        ]
        print(pensamento_personagem(atacante_nome, random.choice(falas), YELLOW))
        return

    falas = [
        "O golpe encontra carne antes que voce encontre defesa.",
        "A pancada vem perfeita, cruel e pesada.",
        "Por um instante, a luta inteira vira dor.",
    ]
    print(colorir(f"{atacante_nome}: \"{random.choice(falas)}\"", RED))
    print(pensamento_personagem(alvo_nome, "Esse doeu diferente. Preciso respeitar essa abertura.", RED))


def rodar_turno_defensivo_inimigo():
    """Sorteia a reacao do monstro ao ataque do jogador."""
    opcoes = ["sem_defesa", "esquivar", "bloquear", "contra_atacar"]
    return random.choices(opcoes, weights=[45, 20, 25, 10])[0]


def _imprimir_opcoes_defesa(atributos_player, efeitos_raciais, precisao_atacante=0, entidade_defensora=None, propriedades_defensor=None):
    penalidade_condicao = calcular_penalidade_reacao_condicoes(entidade_defensora or {})
    propriedades_defensor = propriedades_defensor or {}
    chance_esquiva = calcular_chance_esquiva(atributos_player, efeitos_raciais, precisao_atacante + penalidade_condicao)
    chance_sorte = calcular_chance_sorte_esquiva(atributos_player, efeitos_raciais)
    percentual_bloqueio = calcular_percentual_dano_bloqueio(atributos_player, efeitos_raciais, propriedades_defensor)
    chance_contra_ataque = calcular_chance_contra_ataque(atributos_player, efeitos_raciais, precisao_atacante + penalidade_condicao)

    print(linha_pontilhada(cor=MAGENTA))
    print(colorir("Como voce vai se defender?", BOLD))
    print(
        f"[1] Esquivar ({formatar_percentual(chance_esquiva)} chance - evita 100% / "
        f"sorte {formatar_percentual(chance_sorte)} reduz falha para 80%)"
    )
    print(f"[2] Bloquear (garantido - recebe {formatar_percentual(percentual_bloqueio)} do dano)")
    print(f"[3] Contra-Atacar ({formatar_percentual(chance_contra_ataque)} chance - usa uma habilidade com 80% do dano / falha recebe +10%)")
    print(linha_pontilhada(cor=MAGENTA))


def _preparar_contra_ataque_player(player, atributos_player, efeitos_raciais, propriedades_player):
    print("\n" + pensamento_personagem(player.get("name", "Voce"), "Se eu achar a abertura, preciso saber exatamente como vou responder.", CYAN))
    tipo_ataque, habilidade = _selecionar_habilidade_de_ataque(player)
    if not habilidade:
        return None

    if not jogador_tem_recurso_para_habilidade(player, habilidade):
        resource, value = calcular_custo_habilidade(player, habilidade)
        print(
            "\n" + pensamento_personagem(
                player.get("name", "Voce"),
                f"Quero contra-atacar com {habilidade.get('name', 'essa tecnica')}, mas me faltam {value} {_nome_recurso(resource)}.",
                RED,
            )
        )
        aguardar_enter()
        return None

    dano = calcular_dano_habilidade(
        atributos_player,
        tipo_ataque,
        habilidade,
        efeitos_raciais,
        propriedades_player,
    )
    return {"tipo": tipo_ataque, "habilidade": habilidade, "dano": dano}


def _monstro_ataca_livremente(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais):
    propriedades_player = calcular_propriedades_equipadas(player)
    dano_punicao = max(1, dados_monstro["attack"])
    tipo_dano = dados_monstro.get("attack_type", "fisico")
    precisao_monstro = dados_monstro.get("accuracy", 0)
    dano_punicao, _, _ = processar_defesa(
        dano_punicao,
        "sem_defesa",
        int(propriedades_player.get("defense_bonus", 0)),
        atributos_player,
        efeitos_raciais,
        tipo_dano,
        precisao_monstro,
        propriedades_defensor=propriedades_player,
    )
    player["current_hp"] = max(0, player["current_hp"] - dano_punicao)
    print(f"{nome_monstro} aproveita a abertura e causa {colorir(dano_punicao, RED)} de dano!")
    avisos_quebra = aplicar_desgaste_defensivo(player, "sem_defesa", dano_punicao)
    for aviso in avisos_quebra:
        print(colorir(f"{aviso.get('nome_item', 'Um equipamento')} quebrou com o impacto!", RED))

    condicao_inimigo = dados_monstro.get("on_hit_condition")
    if condicao_inimigo and dano_punicao > 0 and player["current_hp"] > 0:
        bonus_resistencia = obter_bonus_resistencia_condicao(player, condicao_inimigo.get("id"))
        resultado_condicao = tentar_aplicar_condicao(
            player,
            condicao_inimigo,
            atributos_player,
            bonus_resistencia,
        )
        if resultado_condicao.get("mensagem"):
            print(colorir(resultado_condicao["mensagem"], MAGENTA))


def _exibir_mensagens_condicoes(resultado):
    for mensagem in resultado.get("mensagens", []):
        print(colorir(mensagem, MAGENTA))


def _formatar_condicoes(entidade):
    condicoes = entidade.get("conditions", [])
    if not condicoes:
        return ""

    return ", ".join(
        f"{condicao.get('name', condicao.get('id', 'Condicao'))}({condicao.get('duration', 1)}t)"
        for condicao in condicoes
    )


def _executar_turno_monstro(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais, monstro=None):
    propriedades_player = calcular_propriedades_equipadas(player)
    limpar_tela()
    print(caixa_texto(f"Turno de {nome_monstro}", cor=RED))
    print(colorir(f"{player['name']} VS {nome_monstro}", BOLD))
    print(f"{player['name']}: {_formatar_hp(player['current_hp'], player['max_hp'])}")
    if monstro:
        print(f"{nome_monstro}: {colorir(str(monstro['current_hp']) + '/' + str(monstro['max_hp']) + ' HP', RED)}")
    print(
        f"Ataque inimigo: {colorir(dados_monstro['attack'], RED)} | "
        f"Precisao: {formatar_percentual(dados_monstro.get('accuracy', 0))} | "
        f"Dano: {_nome_tipo_dano(dados_monstro)}"
    )
    precisao_monstro = dados_monstro.get("accuracy", 0)
    _imprimir_opcoes_defesa(atributos_player, efeitos_raciais, precisao_monstro, player, propriedades_player)

    def_opcao = str(obter_entrada("Escolha sua postura de defesa: ", opcoes=[1, 2, 3]))
    postura_player = "bloquear"
    contra_preparado = None
    if def_opcao == "1":
        postura_player = "esquivar"
    elif def_opcao == "3":
        postura_player = "contra_atacar"
        contra_preparado = _preparar_contra_ataque_player(player, atributos_player, efeitos_raciais, propriedades_player)
        if not contra_preparado:
            postura_player = "bloquear"
            print("\n" + pensamento_personagem(player.get("name", "Voce"), "Sem tecnica pronta, melhor erguer a guarda.", YELLOW))
            aguardar_enter()

    dano_bruto_inimigo = dados_monstro["attack"]
    tipo_dano_inimigo = dados_monstro.get("attack_type", "fisico")
    dano_sofrido_player, contra_dano_player, msg_player = processar_defesa(
        dano_bruto_inimigo,
        postura_player,
        int(propriedades_player.get("defense_bonus", 0)),
        atributos_player,
        efeitos_raciais,
        tipo_dano_inimigo,
        precisao_monstro,
        propriedades_defensor=propriedades_player,
        dano_contra_ataque=contra_preparado.get("dano") if contra_preparado else None,
    )

    dano_sofrido_player = aplicar_reducao_dano_por_condicoes(player, dano_sofrido_player)
    player["current_hp"] = max(0, player["current_hp"] - dano_sofrido_player)
    print(f"\n-> {msg_player}")
    if dano_sofrido_player > 0:
        print(f"{nome_monstro} causou {colorir(dano_sofrido_player, RED)} de dano a voce.")
        _fala_inimigo(dados_monstro, "hit", nome_monstro)
        avisos_quebra = aplicar_desgaste_defensivo(player, postura_player, dano_sofrido_player)
        for aviso in avisos_quebra:
            print(colorir(f"{aviso.get('nome_item', 'Um equipamento')} quebrou com o impacto!", RED))

    if contra_dano_player > 0:
        recurso_gasto, erro_recurso = preparar_uso_habilidade(player, contra_preparado["habilidade"]) if contra_preparado else (True, None)
        if not recurso_gasto:
            print(pensamento_personagem(player.get("name", "Voce"), erro_recurso or "A abertura veio, mas meu corpo nao respondeu.", RED))
            contra_dano_player = 0
        else:
            calcular_desgaste_arma(player)
            print(pensamento_personagem(player.get("name", "Voce"), f"Peguei a abertura. {contra_dano_player} de volta.", YELLOW))

    return {"contra_dano": contra_dano_player, "dano_player": dano_sofrido_player}


def _nome_recurso(resource):
    nomes = {
        "mana": "Mana",
        "stamina": "Estamina",
    }
    return nomes.get(resource, resource.capitalize())


def _nome_tipo_dano(dados_monstro):
    return "Magico" if dados_monstro.get("attack_type") == "magia" else "Fisico"


def _exibir_habilidade(player, indice, habilidade):
    resource, value = calcular_custo_habilidade(player, habilidade)
    print(
        f"[{indice}] {habilidade['name']} - "
        f"Nv. Skill {habilidade.get('skill_level', 1)} | {habilidade.get('rarity', 'comum')} | "
        f"Custo: {value} {_nome_recurso(resource)} | "
        f"Multiplicador: x{habilidade.get('multiplier', 1)}"
    )
    print(f"    {habilidade.get('description', '')}")


def _escolher_habilidade(player, categoria):
    limpar_tela()
    habilidades = listar_habilidades_conhecidas(player, categoria)
    if not habilidades:
        print("\nVoce ainda nao conhece habilidades dessa categoria.")
        aguardar_enter("Pressione Enter para voltar ao combate...")
        return None

    titulo = "Habilidades Fisicas" if categoria == "fisico" else "Habilidades Magicas"
    print(caixa_texto(titulo, cor=MAGENTA))
    print(f"{player['name']}: {_formatar_mana(player.get('current_mana', 0), player.get('max_mana', 0))} | {_formatar_estamina(player.get('current_stamina', 0), player.get('max_stamina', 0))}")
    print(linha_pontilhada())
    for i, habilidade in enumerate(habilidades, 1):
        _exibir_habilidade(player, i, habilidade)

    print(f"[{len(habilidades) + 1}] Voltar")

    escolha = obter_entrada(
        "Escolha a habilidade: ",
        opcoes=list(range(1, len(habilidades) + 2)),
    ) - 1

    if escolha == len(habilidades):
        return None

    if 0 <= escolha < len(habilidades):
        return habilidades[escolha]

    print("\n" + pensamento_personagem(player.get("name", "Voce"), "Isso nao e uma tecnica. Preciso escolher melhor.", RED))
    return None


def _selecionar_habilidade_de_ataque(player):
    limpar_tela()
    print(caixa_texto("Escolha sua Categoria de Habilidade", cor=MAGENTA))
    print(f"{player['name']}: {_formatar_mana(player.get('current_mana', 0), player.get('max_mana', 0))} | {_formatar_estamina(player.get('current_stamina', 0), player.get('max_stamina', 0))}")
    print(linha_pontilhada())
    print("[1] Habilidades Fisicas")
    print("[2] Habilidades Magicas")
    print("[3] Voltar")
    print(linha_pontilhada())
    sub_opcao = str(obter_entrada(">> ", opcoes=[1, 2, 3]))

    if sub_opcao == "1":
        return "fisico", _escolher_habilidade(player, "fisico")

    if sub_opcao == "2":
        if entidade_tem_condicao(player, "silenced"):
            print(colorir("\nVoce esta Silenciado e nao consegue usar magia agora.", RED))
            aguardar_enter()
            return None, None
        return "magia", _escolher_habilidade(player, "magico")

    return None, None


def _chave_consumivel(item):
    restore = item.get("restore", {})
    return (
        item.get("id", item.get("name", "")),
        item.get("name", ""),
        restore.get("resource", ""),
        restore.get("value", 0),
    )


def _listar_consumiveis_agrupados(player):
    agrupados = {}
    for item in player.get("inventory", []):
        if not item_e_consumivel(item):
            continue

        chave = _chave_consumivel(item)
        if chave not in agrupados:
            agrupados[chave] = {"item": item, "quantidade": 0}
        agrupados[chave]["quantidade"] += obter_quantidade_item(item)

    return list(agrupados.values())


def _usar_item_em_combate(player):
    limpar_tela()
    nome_heroi = player.get("name", "Voce")
    consumiveis = _listar_consumiveis_agrupados(player)
    if not consumiveis:
        print("\n" + pensamento_personagem(nome_heroi, "Nada nas bolsas... pessimo momento para descobrir isso.", RED))
        aguardar_enter("Pressione Enter para escolher outra acao...")
        return False

    print(caixa_texto("Consumiveis Disponiveis", cor=GREEN))
    print(f"{nome_heroi}: {_formatar_hp(player.get('current_hp', 0), player.get('max_hp', 0))} | {_formatar_mana(player.get('current_mana', 0), player.get('max_mana', 0))} | {_formatar_estamina(player.get('current_stamina', 0), player.get('max_stamina', 0))}")
    print(linha_pontilhada())
    for i, entrada in enumerate(consumiveis, 1):
        item = entrada["item"]
        quantidade = entrada["quantidade"]
        descricao = item.get("description", "Sem descricao.")
        print(f"[{i}] {item.get('name', 'Consumivel')} | Quantidade: {quantidade}")
        print(f"    {descricao}")

    voltar = len(consumiveis) + 1
    print(f"[{voltar}] Voltar")

    escolha = obter_entrada(
        "Escolha um item para usar: ",
        opcoes=list(range(1, len(consumiveis) + 2)),
    ) - 1

    if escolha == len(consumiveis):
        return False

    if not 0 <= escolha < len(consumiveis):
        print("\n" + pensamento_personagem(nome_heroi, "Minha mao tremeu. Preciso escolher algo que eu realmente tenha.", RED))
        return False

    item = consumiveis[escolha]["item"]
    resultado = consumir_consumivel(player, item)
    if not resultado.get("sucesso"):
        print("\n" + pensamento_personagem(nome_heroi, resultado.get("mensagem", "Nao da para usar isso agora."), RED))
        aguardar_enter("Pressione Enter para escolher outra acao...")
        return False

    _exibir_resultado_consumivel(player, resultado)
    aguardar_enter("\nPressione Enter para o inimigo reagir...")
    return True


def _calcular_penalidade_derrota(player, chefe=False):
    ouro_atual = max(0, int(player.get("gold", 0)))
    percentual_ouro = 0.25 if chefe else 0.15

    ouro_perdido = min(ouro_atual, max(5 if ouro_atual > 0 else 0, int(round(ouro_atual * percentual_ouro))))
    return ouro_perdido, 0


def _processar_derrota(player, dados_monstro, nome_monstro, pode_fugir):
    chefe = not pode_fugir
    ouro_perdido, xp_perdido = _calcular_penalidade_derrota(player, chefe)

    player["gold"] = max(0, int(player.get("gold", 0)) - ouro_perdido)
    player["xp"] = max(0, int(player.get("xp", 0)))
    player["current_hp"] = max(1, int(player.get("max_hp", 1) * 0.20))
    player["current_mana"] = max(0, int(player.get("max_mana", 0) * 0.15))
    player["current_stamina"] = max(0, int(player.get("max_stamina", 0) * 0.15))
    player["defeats"] = int(player.get("defeats", 0)) + 1
    salvar_json("data/core/player.json", player)
    player["_derrota_recente"] = True

    limpar_tela()
    print(caixa_texto("VOCE CAIU EM COMBATE", cor=RED))
    _fala_inimigo(dados_monstro, "victory", nome_monstro)
    print(linha_pontilhada(cor=MAGENTA))
    print(pensamento_personagem(player.get("name", "Voce"), "Nao foi morte. Foi pior: sobrevivi o bastante para lembrar.", RED))
    if chefe:
        print(pensamento_personagem(player.get("name", "Voce"), "Chefe nao da segunda chance de graca. Eu entrei sabendo disso... ou deveria saber.", RED))
    else:
        print(pensamento_personagem(player.get("name", "Voce"), "A trilha me cuspiu de volta. Da proxima vez, eu volto menos arrogante.", CYAN))
    print(linha_pontilhada(cor=MAGENTA))
    print(colorir(f"Ouro perdido: {ouro_perdido}G", YELLOW))
    print(colorir(f"XP total preservado: {player['xp']}", YELLOW))
    print(f"HP: {_formatar_hp(player['current_hp'], player['max_hp'])}")
    print(f"Mana: {_formatar_mana(player.get('current_mana', 0), player.get('max_mana', 0))}")
    print(f"Estamina: {_formatar_estamina(player.get('current_stamina', 0), player.get('max_stamina', 0))}")
    print(linha_pontilhada(cor=MAGENTA))
    print(pensamento_personagem(player.get("name", "Voce"), "Preciso descansar, me recompor, e escolher melhor a hora de encarar o abismo.", CYAN))
    aguardar_enter("\nPressione Enter para acordar na vila...")


def combater(player, enemy_id, pode_fugir=True):
    if garantir_estrutura_evolucao(player):
        salvar_json("data/core/player.json", player)

    dados_monstro = carregar_dados_monstro(enemy_id)
    if not dados_monstro:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Tem algo errado nesta trilha... nem o mundo sabe que criatura era essa.", RED))
        return False
    registrar_encontro(player, enemy_id)
    dados_monstro = escalar_monstro_para_level(dados_monstro, player.get("level", 1))

    nome_monstro = dados_monstro["name"]
    monstro = {
        "name": nome_monstro,
        "current_hp": dados_monstro["hp"],
        "max_hp": dados_monstro["hp"],
        "conditions": [],
    }
    monstro_hp = monstro["current_hp"]
    monstro_max_hp = monstro["max_hp"]
    efeitos_raciais = obter_efeitos_raciais(player)

    limpar_tela()
    print(caixa_texto(f"UM INIMIGO SE APROXIMA: {nome_monstro.upper()}", cor=RED))
    _fala_inimigo(dados_monstro, "intro", nome_monstro)
    aguardar_enter("\nPressione Enter para assumir postura de combate...")

    while player["current_hp"] > 0 and monstro_hp > 0:
        limpar_tela()
        resultado_condicoes_player = processar_condicoes_inicio_turno(player)
        _exibir_mensagens_condicoes(resultado_condicoes_player)
        if player["current_hp"] <= 0:
            break

        atributos_player = calcular_atributos_totais(player)
        propriedades_player = calcular_propriedades_equipadas(player)
        chance_fuga = calcular_chance_fuga(atributos_player, efeitos_raciais, propriedades_player)

        hp_player = _formatar_hp(player["current_hp"], player["max_hp"])
        hp_monstro = colorir(f"{monstro['current_hp']}/{monstro_max_hp} HP", RED)
        mana = _formatar_mana(player.get("current_mana", 0), player.get("max_mana", 0))
        estamina = _formatar_estamina(player.get("current_stamina", 0), player.get("max_stamina", 0))

        print(caixa_texto(f"Turno de {player['name']}", cor=CYAN))
        print(colorir(f"{player['name']} VS {nome_monstro}", BOLD))
        print(f"Nivel {player.get('level', 1)} vs Nivel {dados_monstro.get('level', 1)}")
        print(f"{player['name']}: {hp_player}    {nome_monstro}: {hp_monstro}")
        print(f"{mana} | {estamina}")
        condicoes_player = _formatar_condicoes(player)
        if condicoes_player:
            print(colorir(f"Condicoes: {condicoes_player}", MAGENTA))
        condicoes_monstro = _formatar_condicoes(monstro)
        if condicoes_monstro:
            print(colorir(f"{nome_monstro}: {condicoes_monstro}", MAGENTA))
        print(linha_pontilhada())
        print("[1] Atacar")
        print("[2] Analisar Combate")
        print("[3] Usar Item")
        print(f"[4] Tentar Fugir ({formatar_percentual(chance_fuga)} chance)")
        print(linha_pontilhada())

        opcao = str(obter_entrada("Escolha sua acao: ", opcoes=[1, 2, 3, 4]))

        if opcao == "1":
            tipo_ataque, habilidade = _selecionar_habilidade_de_ataque(player)
            if not habilidade:
                continue

            if not jogador_tem_recurso_para_habilidade(player, habilidade):
                cost = habilidade.get("cost", {})
                print(
                    "\n" + pensamento_personagem(
                        player["name"],
                        f"Ainda nao tenho folego para {habilidade['name']}... preciso de {cost.get('value', 0)} {_nome_recurso(cost.get('resource', ''))}.",
                        RED,
                    )
                )
                aguardar_enter("Pressione Enter para escolher outra acao...")
                continue

            recurso_gasto, erro_recurso = preparar_uso_habilidade(player, habilidade)
            if not recurso_gasto:
                print("\n" + pensamento_personagem(player["name"], erro_recurso or "Nao consigo puxar essa tecnica agora.", RED))
                aguardar_enter("Pressione Enter para escolher outra acao...")
                continue

            dano_bruto = calcular_dano_habilidade(
                atributos_player,
                tipo_ataque,
                habilidade,
                efeitos_raciais,
                propriedades_player,
            )
            chance_critico = (
                calcular_chance_critico(efeitos_raciais, propriedades_player)
                + calcular_bonus_critico_condicoes(player)
            )
            if random.random() <= chance_critico:
                bonus_dano_critico = max(0, propriedades_player.get("crit_damage_multiplier_bonus", 0))
                dano_bruto = int(round(dano_bruto * (2 + bonus_dano_critico)))
                _exibir_ataque_critico(player["name"], nome_monstro, atacante_e_player=True)
            calcular_desgaste_arma(player)
            print("\n" + pensamento_personagem(player["name"], f"{habilidade['name']}. Sem hesitar.", YELLOW))

            postura_inimiga = rodar_turno_defensivo_inimigo()
            print(f"\n{nome_monstro} se prepara para: {postura_inimiga.upper()}!")

            dano_sofrido_inimigo, contra_dano, msg = processar_defesa(
                dano_bruto,
                postura_inimiga,
                dados_monstro["defense"],
                contra_ataque_evita_dano=False,
                dano_contra_ataque=dados_monstro.get("attack", dano_bruto),
            )

            dano_sofrido_inimigo = aplicar_reducao_dano_por_condicoes(monstro, dano_sofrido_inimigo)
            monstro["current_hp"] = max(0, monstro["current_hp"] - dano_sofrido_inimigo)
            monstro_hp = monstro["current_hp"]
            print(f"-> {msg}")
            if dano_sofrido_inimigo > 0:
                print(pensamento_personagem(player["name"], f"O golpe entrou. {dano_sofrido_inimigo} de dano em {nome_monstro}.", YELLOW))
                if monstro["current_hp"] <= monstro_max_hp * 0.30:
                    _fala_inimigo(dados_monstro, "low_hp", nome_monstro)
                else:
                    _fala_inimigo(dados_monstro, "damaged", nome_monstro)
                condicao_skill = habilidade.get("applies_condition")
                if condicao_skill:
                    resultado_condicao = tentar_aplicar_condicao(monstro, condicao_skill)
                    if resultado_condicao.get("mensagem"):
                        print(colorir(resultado_condicao["mensagem"], MAGENTA))
                for condicao_item in obter_condicoes_ao_acertar(player):
                    resultado_condicao = tentar_aplicar_condicao(monstro, condicao_item)
                    if resultado_condicao.get("mensagem"):
                        print(colorir(resultado_condicao["mensagem"], MAGENTA))

            if contra_dano > 0:
                player["current_hp"] = max(0, player["current_hp"] - contra_dano)
                print(pensamento_personagem(player["name"], f"Ele respondeu rapido demais. {contra_dano} de dano.", RED))
                if player["current_hp"] <= 0:
                    break

            if monstro_hp <= 0:
                break

            aguardar_enter("\nPressione Enter para o turno do inimigo...")

            resultado_condicoes_monstro = processar_condicoes_inicio_turno(monstro)
            _exibir_mensagens_condicoes(resultado_condicoes_monstro)
            if resultado_condicoes_monstro.get("mensagens"):
                aguardar_enter("\nPressione Enter para reagir ao avanco inimigo...")
            monstro_hp = monstro["current_hp"]
            if monstro_hp <= 0:
                break

            resultado_turno_monstro = _executar_turno_monstro(
                player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais, monstro
            )
            contra_dano_player = resultado_turno_monstro["contra_dano"]
            if contra_dano_player > 0:
                monstro["current_hp"] = max(0, monstro["current_hp"] - contra_dano_player)
            monstro_hp = monstro["current_hp"]

            condicao_inimigo = dados_monstro.get("on_hit_condition")
            if condicao_inimigo and player["current_hp"] > 0 and resultado_turno_monstro["dano_player"] > 0:
                bonus_resistencia = obter_bonus_resistencia_condicao(player, condicao_inimigo.get("id"))
                resultado_condicao = tentar_aplicar_condicao(
                    player,
                    condicao_inimigo,
                    atributos_player,
                    bonus_resistencia,
                )
                if resultado_condicao.get("mensagem"):
                    print(colorir(resultado_condicao["mensagem"], MAGENTA))

            if player["current_hp"] > 0 and monstro_hp > 0:
                aguardar_enter("\nPressione Enter para o proximo turno...")

        elif opcao == "2":
            limpar_tela()
            print(caixa_texto("Analise de Combate", cor=MAGENTA))
            print(f"{nome_monstro}: {colorir(f'{monstro_hp}/{monstro_max_hp} HP', RED)} | Ataque {dados_monstro['attack']} | Defesa {dados_monstro['defense']}")
            if monstro.get("conditions"):
                print("Condicoes: " + _formatar_condicoes(monstro))
            aguardar_enter("Pressione Enter para voltar ao combate...")

        elif opcao == "3":
            item_usado = _usar_item_em_combate(player)
            if not item_usado:
                continue

            atributos_player = calcular_atributos_totais(player)
            resultado_turno_monstro = _executar_turno_monstro(
                player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais, monstro
            )
            contra_dano_player = resultado_turno_monstro["contra_dano"]
            if contra_dano_player > 0:
                monstro["current_hp"] = max(0, monstro["current_hp"] - contra_dano_player)
            monstro_hp = monstro["current_hp"]

            condicao_inimigo = dados_monstro.get("on_hit_condition")
            if condicao_inimigo and player["current_hp"] > 0 and resultado_turno_monstro["dano_player"] > 0:
                bonus_resistencia = obter_bonus_resistencia_condicao(player, condicao_inimigo.get("id"))
                resultado_condicao = tentar_aplicar_condicao(
                    player,
                    condicao_inimigo,
                    atributos_player,
                    bonus_resistencia,
                )
                if resultado_condicao.get("mensagem"):
                    print(colorir(resultado_condicao["mensagem"], MAGENTA))

            if player["current_hp"] > 0 and monstro_hp > 0:
                aguardar_enter("\nPressione Enter para o proximo turno...")

        elif opcao == "4":
            if not pode_fugir:
                print("\n" + pensamento_personagem(player["name"], "Nao tem saida. Esse monstro esta entre mim e qualquer rota de fuga.", RED))
                aguardar_enter("Pressione Enter para voltar a luta...")
                continue

            if random.random() <= chance_fuga:
                print("\n" + pensamento_personagem(player["name"], "Dessa vez, viver e vencer sao a mesma coisa. Hora de sair.", GREEN))
                return False

            print("\n" + pensamento_personagem(player["name"], "Droga. Corri no tempo errado.", RED))
            _monstro_ataca_livremente(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais)
            if player["current_hp"] > 0:
                aguardar_enter("\nPressione Enter para recuperar o folego...")

        else:
            print("\n" + pensamento_personagem(player["name"], "Foco. Uma escolha errada aqui vira epitafio.", RED))

    if player["current_hp"] <= 0:
        _processar_derrota(player, dados_monstro, nome_monstro, pode_fugir)
        return False

    print(colorir(f"\n{player['name']}: 'Caiu. Ainda estou respirando.'", GREEN))
    print(colorir(f"{nome_monstro} desaba sem vida no chao.", GREEN))
    registrar_derrota_inimigo(player, enemy_id)
    recompensas = processar_vitoria(player, dados_monstro)
    materiais = recompensas.get("materiais", [])
    print(
        pensamento_personagem(
            player["name"],
            f"Recompensa: +{recompensas.get('xp_ganho', 0)} XP e +{recompensas.get('gold_ganho', 0)}G.",
            YELLOW,
        )
    )
    if materiais:
        print(f"Materiais coletados para Craft: {', '.join(materiais)}")
    aguardar_enter("\nPressione Enter para coletar os espolios...")
    exibir_tela_level_up(player, recompensas.get("resultado_xp"))
    return True
