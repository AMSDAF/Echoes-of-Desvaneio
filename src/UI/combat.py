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
    obter_entrada,
)
from src.services.attribute_service import formatar_percentual
from src.services.bestiary_service import registrar_derrota_inimigo, registrar_encontro
from src.services.combat_service import (
    calcular_chance_contra_ataque,
    calcular_chance_esquiva,
    calcular_chance_fuga,
    calcular_chance_critico,
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


def _fala_inimigo(dados_monstro, momento, nome_monstro=None):
    linhas = dados_monstro.get("battle_lines", {}).get(momento, [])
    if not linhas:
        return

    nome = nome_monstro or dados_monstro.get("name", "Inimigo")
    print(colorir(f"{nome}: \"{random.choice(linhas)}\"", MAGENTA))


def rodar_turno_defensivo_inimigo():
    """Sorteia a reacao do monstro ao ataque do jogador."""
    opcoes = ["sem_defesa", "esquivar", "bloquear", "contra_atacar"]
    return random.choices(opcoes, weights=[45, 20, 25, 10])[0]


def _imprimir_opcoes_defesa(atributos_player, efeitos_raciais, precisao_atacante=0, entidade_defensora=None):
    penalidade_condicao = calcular_penalidade_reacao_condicoes(entidade_defensora or {})
    chance_esquiva = calcular_chance_esquiva(atributos_player, efeitos_raciais, precisao_atacante + penalidade_condicao)
    percentual_bloqueio = calcular_percentual_dano_bloqueio(atributos_player, efeitos_raciais)
    chance_contra_ataque = calcular_chance_contra_ataque(atributos_player, efeitos_raciais, precisao_atacante + penalidade_condicao)

    print(linha_pontilhada())
    print(colorir("Como voce vai se defender?", BOLD))
    print(f"[1] Esquivar ({formatar_percentual(chance_esquiva)} chance - evita dano / falha recebe 50%)")
    print(f"[2] Bloquear (garantido - recebe {formatar_percentual(percentual_bloqueio)} do dano)")
    print(f"[3] Contra-Atacar ({formatar_percentual(chance_contra_ataque)} chance - causa 50% de dano / falha recebe +25%)")


def _monstro_ataca_livremente(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais):
    propriedades_player = calcular_propriedades_equipadas(player)
    dano_punicao = max(1, dados_monstro["attack"])
    tipo_dano = dados_monstro.get("attack_type", "fisico")
    precisao_monstro = dados_monstro.get("accuracy", 0)
    dano_punicao, _, _ = processar_defesa(
        dano_punicao,
        "sem_defesa",
        0,
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


def _executar_turno_monstro(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais):
    propriedades_player = calcular_propriedades_equipadas(player)
    print(caixa_texto(f"Turno de {nome_monstro}", cor=RED))
    precisao_monstro = dados_monstro.get("accuracy", 0)
    _imprimir_opcoes_defesa(atributos_player, efeitos_raciais, precisao_monstro, player)

    def_opcao = str(obter_entrada("Escolha sua postura de defesa: ", opcoes=[1, 2, 3]))
    postura_player = "bloquear"
    if def_opcao == "1":
        postura_player = "esquivar"
    elif def_opcao == "3":
        postura_player = "contra_atacar"

    dano_bruto_inimigo = dados_monstro["attack"]
    tipo_dano_inimigo = dados_monstro.get("attack_type", "fisico")
    dano_sofrido_player, contra_dano_player, msg_player = processar_defesa(
        dano_bruto_inimigo,
        postura_player,
        0,
        atributos_player,
        efeitos_raciais,
        tipo_dano_inimigo,
        precisao_monstro,
        propriedades_defensor=propriedades_player,
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
        print(pensamento_personagem(player.get("name", "Voce"), f"Peguei a abertura. {contra_dano_player} de volta.", YELLOW))

    return {"contra_dano": contra_dano_player, "dano_player": dano_sofrido_player}


def _nome_recurso(resource):
    nomes = {
        "mana": "Mana",
        "stamina": "Estamina",
    }
    return nomes.get(resource, resource.capitalize())


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
    habilidades = listar_habilidades_conhecidas(player, categoria)
    if not habilidades:
        print("\nVoce ainda nao conhece habilidades dessa categoria.")
        aguardar_enter("Pressione Enter para voltar ao combate...")
        return None

    print(caixa_texto("Habilidades Disponiveis", cor=MAGENTA))
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
    print(caixa_texto("Escolha sua Categoria de Habilidade", cor=MAGENTA))
    print("[1] Habilidades Fisicas")
    print("[2] Habilidades Magicas")
    print("[3] Voltar")
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
        agrupados[chave]["quantidade"] += 1

    return list(agrupados.values())


def _usar_item_em_combate(player):
    nome_heroi = player.get("name", "Voce")
    consumiveis = _listar_consumiveis_agrupados(player)
    if not consumiveis:
        print("\n" + pensamento_personagem(nome_heroi, "Nada nas bolsas... pessimo momento para descobrir isso.", RED))
        aguardar_enter("Pressione Enter para escolher outra acao...")
        return False

    print(caixa_texto("Consumiveis Disponiveis", cor=GREEN))
    for i, entrada in enumerate(consumiveis, 1):
        item = entrada["item"]
        quantidade = entrada["quantidade"]
        descricao = item.get("description", "Sem descricao.")
        print(f"[{i}] {item.get('name', 'Consumivel')} x{quantidade}")
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

    nome_item = resultado["item_name"]
    print("\n" + pensamento_personagem(nome_heroi, f"Agora. {nome_item} pode me manter de pe.", GREEN))
    if "resource" in resultado:
        print(
            pensamento_personagem(
                nome_heroi,
                f"Sinto {resultado['restored']} de {resultado['resource_name']} voltando.",
                _cor_recurso(resultado["resource"]),
            )
        )
    elif "condition_removed" in resultado:
        print(pensamento_personagem(nome_heroi, f"{resultado['condition_name']} perdeu a forca. Melhor.", GREEN))
    elif "condition_applied" in resultado:
        print(pensamento_personagem(nome_heroi, f"{resultado['condition_name']} esta comigo por {resultado.get('duration', 1)} turnos.", MAGENTA))
    return True


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

    print(caixa_texto(f"UM INIMIGO SE APROXIMA: {nome_monstro.upper()}", cor=RED))
    _fala_inimigo(dados_monstro, "intro", nome_monstro)

    while player["current_hp"] > 0 and monstro_hp > 0:
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

        print(caixa_texto(f"{player['name']} VS {nome_monstro}", cor=CYAN))
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
                print(colorir("\nAcerto critico! O golpe encontra uma abertura perfeita.", YELLOW))
            calcular_desgaste_arma(player)
            print("\n" + pensamento_personagem(player["name"], f"{habilidade['name']}. Sem hesitar.", YELLOW))

            postura_inimiga = rodar_turno_defensivo_inimigo()
            print(f"\n{nome_monstro} se prepara para: {postura_inimiga.upper()}!")

            dano_sofrido_inimigo, contra_dano, msg = processar_defesa(
                dano_bruto,
                postura_inimiga,
                dados_monstro["defense"],
                contra_ataque_evita_dano=False,
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

            resultado_condicoes_monstro = processar_condicoes_inicio_turno(monstro)
            _exibir_mensagens_condicoes(resultado_condicoes_monstro)
            monstro_hp = monstro["current_hp"]
            if monstro_hp <= 0:
                break

            resultado_turno_monstro = _executar_turno_monstro(
                player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais
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

        elif opcao == "2":
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
                player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais
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

        else:
            print("\n" + pensamento_personagem(player["name"], "Foco. Uma escolha errada aqui vira epitafio.", RED))

    if player["current_hp"] <= 0:
        print(colorir(f"\n{player['name']}: 'Nao... ainda nao...'", RED))
        _fala_inimigo(dados_monstro, "victory", nome_monstro)
        player["current_hp"] = int(player["max_hp"] * 0.20)
        player["gold"] = max(0, player["gold"] - 20)
        salvar_json("data/core/player.json", player)
        return False

    print(colorir(f"\n{player['name']}: 'Caiu. Ainda estou respirando.'", GREEN))
    print(colorir(f"{nome_monstro} desaba sem vida no chao.", GREEN))
    registrar_derrota_inimigo(player, enemy_id)
    materiais = processar_vitoria(player, dados_monstro)
    print(pensamento_personagem(player["name"], f"Recompensa justa: +{dados_monstro['xp_drop']} XP e +{dados_monstro['gold_drop']}G.", YELLOW))
    if materiais:
        print(f"Materiais coletados para Craft: {', '.join(materiais)}")
    aguardar_enter("\nPressione Enter para coletar os espolios...")
    return True
