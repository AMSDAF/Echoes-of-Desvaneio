from src.UI.utils.colors import (
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    caixa_texto,
    colorir,
    fala_entidade,
    linha_pontilhada,
    aguardar_enter,
    limpar_tela,
    obter_entrada,
    pensamento_personagem,
)
from src.services.database import carregar_json, salvar_json
from src.services.equipment_upgrade_service import (
    aprimorar_grau_item,
    aprimoramento_grau_disponivel,
    avaliar_aprimoramento_grau,
    avaliar_receita,
    carregar_receitas_melhoria,
    listar_itens_aprimoraveis_grau,
    melhorar_equipamento,
    obter_item_banco,
    receita_disponivel,
)
from src.services.event_service import resolver_evento_urbano
from src.services.item_service import (
    equipar_item,
    formatar_nome_com_quantidade,
    formatar_nome_com_grau,
    formatar_propriedades_item,
    obter_quantidade_item,
)
from src.services.shop_service import (
    calcular_desconto_carisma,
    calcular_preco_final,
    calcular_valor_venda,
    jogador_tem_item_raro_da_loja,
    listar_itens_vendiveis,
    obter_memoria_loja,
    registrar_compra_loja,
    registrar_visita_loja,
    tentar_comprar_item,
    vender_item,
)


def _formatar_modificadores(item):
    restore = item.get("restore")
    if restore:
        nomes_recursos = {
            "hp": "Vida",
            "mana": "Mana",
            "stamina": "Estamina",
        }
        resource = restore.get("resource")
        value = restore.get("value", 0)
        return f"{nomes_recursos.get(resource, resource)} +{value}"

    modifiers = item.get("modifiers", {})
    propriedades = formatar_propriedades_item(item)
    if not modifiers and not propriedades:
        return "sem modificadores"

    partes = []
    for attr, val in modifiers.items():
        sinal = "+" if val >= 0 else ""
        partes.append(f"{attr.capitalize()} {sinal}{val}")

    partes.extend(propriedades)
    return ", ".join(partes)


def _formatar_meta_item(item):
    nivel = item.get("level_required", 1)
    raridade = item.get("rarity", "comum")
    return f"Nv. {nivel} | {raridade}"


def _formatar_item_venda(item):
    if item.get("type") == "material" or item.get("category") in {"material", "valuable", "quest", "special"}:
        categoria = item.get("category", item.get("type", "material"))
        return categoria

    mods = _formatar_modificadores(item)
    durabilidade = ""
    if item.get("slot") not in {"consumable", "potion", None}:
        durabilidade_atual = item.get("current_durability", item.get("durability", 100))
        durabilidade_maxima = item.get("max_durability", 100)
        durabilidade = f" | Durabilidade: {durabilidade_atual}/{durabilidade_maxima}"

    return f"{item.get('slot', 'item')} | {mods}{durabilidade}"


def _escolher_quantidade_venda(item):
    quantidade = obter_quantidade_item(item)
    if quantidade <= 1:
        return 1

    while True:
        limpar_tela()
        print(caixa_texto("QUANTIDADE PARA VENDER", cor=MAGENTA))
        print(f"Item: {formatar_nome_com_quantidade(item)}")
        print(f"Valor unitario: {colorir(str(calcular_valor_venda(item)) + 'G', YELLOW)}")
        print(linha_pontilhada())
        print("[1] Vender 1")
        print("[2] Vender 5")
        print("[3] Vender 10")
        print("[4] Vender todos")
        print("[5] Escolher quantidade")
        print("[6] Cancelar")
        print(linha_pontilhada())

        escolha = obter_entrada("Escolha: ", opcoes=[1, 2, 3, 4, 5, 6])
        if escolha == 1:
            return 1
        if escolha == 2:
            return min(5, quantidade)
        if escolha == 3:
            return min(10, quantidade)
        if escolha == 4:
            return quantidade
        if escolha == 5:
            while True:
                quantidade_manual = obter_entrada(f"Quantidade (1-{quantidade}): ")
                if 1 <= quantidade_manual <= quantidade:
                    return quantidade_manual
                print(colorir("Quantidade invalida para essa pilha.", RED))
        return 0


def _exibir_evento_mercado(player):
    resultado = resolver_evento_urbano(player, "market")
    if not resultado:
        print("\n" + pensamento_personagem(player.get("name", "Voce"), "Nada chama minha atencao hoje. So moeda trocando de dono.", CYAN))
        return

    print(caixa_texto(resultado.get("title", "Evento"), cor=MAGENTA))
    if resultado.get("text"):
        print(resultado["text"])

    check = resultado.get("check")
    if check:
        sinal = "+" if check["modificador"] >= 0 else ""
        print(
            f"Teste: d20({check['rolagem']}) {sinal}{check['modificador']} "
            f"= {check['total']} vs CD {check['dc']}"
        )
        if check["sucesso"]:
            print(pensamento_personagem(player.get("name", "Voce"), "Li bem a situacao. Isso pode render algo.", GREEN))
        else:
            print(pensamento_personagem(player.get("name", "Voce"), "A oportunidade passou antes de eu entender o preco.", RED))

    for mensagem in resultado.get("messages", []):
        print(colorir(mensagem, CYAN if "Missao aceita" not in mensagem else GREEN))


def _exibir_dialogo_inicial(player, vendedor, dialogos, itens_disponiveis, memoria_loja):
    if jogador_tem_item_raro_da_loja(player, itens_disponiveis):
        print(f"{vendedor}: \"{dialogos['inveja']}\"")
    elif int(memoria_loja.get("visits", 0)) > 0:
        print(f"{vendedor}: \"{dialogos['retorno']}\"")
    else:
        print(f"{vendedor}: \"{dialogos['primeira_vez']}\"")


def _exibir_aviso_item_acima_do_nivel(player, vendedor, dialogos, item):
    nivel_requerido = item.get("level_required", 1)
    fala_padrao = (
        f"Eu vendo, mas nao prometo que voce aguente usar isso hoje. Esse item pede nivel {nivel_requerido}."
    )
    print("\n" + fala_entidade(vendedor, dialogos.get("aviso_nivel_item", fala_padrao), YELLOW))
    print(
        pensamento_personagem(
            player.get("name", "Voce"),
            f"Consigo comprar {item.get('name', 'isso')}. Usar sem pagar vergonha ja e outra historia.",
            YELLOW,
        )
    )


def _obter_id_loja(dados_loja, opcao_menu):
    return str(dados_loja.get("id") or opcao_menu)


def _loja_tem_melhoria(local_id, dados_loja):
    if local_id == "oakridge":
        return False

    servicos = set(dados_loja.get("services", []))
    nome_loja = str(dados_loja.get("nome", "")).lower()
    return "equipment_upgrade" in servicos or "forja" in nome_loja or "forge" in nome_loja


def _nome_item_por_id(item_id):
    dados = obter_item_banco(item_id)
    return (dados or {}).get("name", item_id)


def _simbolo_requisito(ok):
    return colorir("[OK] tem", GREEN) if ok else colorir("[FALTA]", RED)


def _perguntar_equipar_item(player, item):
    if item.get("slot") == "consumable":
        salvar_json("data/core/player.json", player)
        aguardar_enter()
        return

    if player.get("level", 1) < item.get("level_required", 1):
        print(
            pensamento_personagem(
                player.get("name", "Voce"),
                f"Vou guardar {item.get('name', 'Item')}. Ainda preciso chegar ao nivel {item.get('level_required', 1)} para usar isso direito.",
                YELLOW,
            )
        )
        salvar_json("data/core/player.json", player)
        aguardar_enter()
        return

    resposta = obter_entrada(
        f"Deseja equipar {item.get('name', 'este item')} agora? (S/N): ",
        tipo=str,
    ).strip().lower()
    if resposta == "s":
        if equipar_item(player, item):
            print(pensamento_personagem(player.get("name", "Voce"), f"{item.get('name', 'Item')} assenta bem. Da para sentir a diferenca.", GREEN))
        else:
            print(pensamento_personagem(player.get("name", "Voce"), f"Melhor guardar {item.get('name', 'Item')} por enquanto.", GREEN))
            salvar_json("data/core/player.json", player)
        aguardar_enter()
        return

    print(pensamento_personagem(player.get("name", "Voce"), f"{item.get('name', 'Item')} vai para a mochila. Talvez brilhe na hora certa.", GREEN))
    salvar_json("data/core/player.json", player)
    aguardar_enter()


def visitar_comercio(player):
    dados_comercio_geral = carregar_json("data/core/shops.json")

    local_atual = player.get("current_location", "phandalin")
    dados_da_vila = dados_comercio_geral[local_atual]
    lojas_da_vila = dados_da_vila["lojas"]

    while True:
        limpar_tela()
        print(caixa_texto(f"COMERCIO: {dados_da_vila['nome_exibicao']}", cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player['gold']) + 'G', YELLOW)}")
        print(linha_pontilhada())

        for opcao, dados_loja in lojas_da_vila.items():
            print(f"[{opcao}] {dados_loja['nome']}")

        opcao_sair = str(len(lojas_da_vila) + 1)
        print(f"[{opcao_sair}] Voltar para a Vila (Menu Principal)")
        print(linha_pontilhada())

        escolha = str(obter_entrada("Onde deseja ir? ", opcoes=[int(op) for op in lojas_da_vila] + [int(opcao_sair)]))

        if escolha == opcao_sair:
            print("\n" + pensamento_personagem(player.get("name", "Voce"), "Chega de vitrines. A estrada nao espera.", GREEN))
            break
        elif escolha in lojas_da_vila:
            loja_escolhida = lojas_da_vila[escolha]
            itens = carregar_json(loja_escolhida["arquivo"])
            abrir_barraca(player, itens, loja_escolhida, local_atual, _obter_id_loja(loja_escolhida, escolha))
        else:
            print("\n" + pensamento_personagem(player.get("name", "Voce"), "Estou olhando para o lugar errado.", RED))


def abrir_barraca(player, itens_disponiveis, dados_loja, local_id, loja_id):
    nome_da_barraca = dados_loja["nome"]
    vendedor = dados_loja["vendedor"]
    dialogos = dados_loja["dialogos"]
    memoria_loja = obter_memoria_loja(player, local_id, loja_id)

    print(caixa_texto(f"Ao se aproximar de: {nome_da_barraca.upper()}", cor=MAGENTA))
    _exibir_dialogo_inicial(player, vendedor, dialogos, itens_disponiveis, memoria_loja)
    registrar_visita_loja(player, local_id, loja_id)

    aguardar_enter("\nPressione Enter para ver as mercadorias...")

    while True:
        limpar_tela()
        print(caixa_texto(nome_da_barraca.upper(), cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player['gold']) + 'G', YELLOW)}")
        print(linha_pontilhada())
        loja_melhora_equipamento = _loja_tem_melhoria(local_id, dados_loja)
        if loja_melhora_equipamento:
            print("[1] Melhorar equipamento")
            print("[2] Comprar")
            print("[3] Vender Itens")
            print("[4] Conversar / Procurar Rumores")
            print("[5] Voltar")
            opcoes_menu = [1, 2, 3, 4, 5]
            opcao_voltar = 5
        else:
            print("[1] Comprar")
            print("[2] Vender Itens")
            print("[3] Conversar / Procurar Rumores")
            print("[4] Voltar")
            opcoes_menu = [1, 2, 3, 4]
            opcao_voltar = 4
        print(linha_pontilhada())

        acao_loja = obter_entrada("O que deseja fazer? ", opcoes=opcoes_menu)
        if acao_loja == 1 and loja_melhora_equipamento:
            _melhorar_equipamento_na_forja(player, vendedor, local_id)
        elif acao_loja == 1:
            _comprar_item_na_barraca(player, itens_disponiveis, vendedor, dialogos, local_id, loja_id)
        elif acao_loja == 2 and loja_melhora_equipamento:
            _comprar_item_na_barraca(player, itens_disponiveis, vendedor, dialogos, local_id, loja_id)
        elif acao_loja == 2:
            _vender_item_na_barraca(player, vendedor)
        elif acao_loja == 3 and loja_melhora_equipamento:
            _vender_item_na_barraca(player, vendedor)
        elif acao_loja == 3:
            _exibir_evento_mercado(player)
            aguardar_enter()
        elif acao_loja == 4 and loja_melhora_equipamento:
            _exibir_evento_mercado(player)
            aguardar_enter()
        elif acao_loja == opcao_voltar:
            break
        else:
            break


def _exibir_requisitos_receita(player, receita):
    avaliacao = avaliar_receita(player, receita)
    base_id = receita.get("base_item")
    resultado_id = receita.get("result_item")

    print(f"Base: {_nome_item_por_id(base_id)} - {_simbolo_requisito(avaliacao['base_ok'])}")
    print(f"Resultado: {colorir(_nome_item_por_id(resultado_id), CYAN)}")
    print(
        f"Ouro: {avaliacao['gold_current']}/{avaliacao['gold_required']}G "
        f"- {_simbolo_requisito(avaliacao['gold_ok'])}"
    )
    print("Materiais:")
    if not avaliacao["materials"]:
        print("  - Nenhum")
    for material_id, dados in avaliacao["materials"].items():
        print(
            f"  - {_nome_item_por_id(material_id)}: "
            f"{dados['current']}/{dados['required']} - {_simbolo_requisito(dados['ok'])}"
        )


def _melhorar_equipamento_na_forja(player, vendedor, local_id):
    while True:
        limpar_tela()
        print(caixa_texto("MELHORIAS DA FORJA", cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}")
        print(fala_entidade(vendedor, "Posso transformar sucata em arma melhor ou puxar mais um grau do que voce ja tem.", CYAN))
        print(linha_pontilhada())
        print("[1] Transformar equipamento por receita")
        print("[2] Aprimorar grau de equipamento")
        print("[3] Voltar")
        escolha = obter_entrada("Escolha: ", opcoes=[1, 2, 3])

        if escolha == 1:
            _melhorar_por_receita_na_forja(player, vendedor, local_id)
        elif escolha == 2:
            _aprimorar_grau_na_forja(player, vendedor)
        else:
            return


def _melhorar_por_receita_na_forja(player, vendedor, local_id):
    receitas = carregar_receitas_melhoria(local_id, "forge")
    if not receitas:
        print(fala_entidade(vendedor, "Ainda nao tenho receitas de melhoria prontas.", RED))
        aguardar_enter()
        return

    while True:
        limpar_tela()
        print(caixa_texto("MELHORIAS DA FORJA", cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}")
        print(fala_entidade(vendedor, "Equipamento fraco, material certo e um pouco de ouro. Ai nasce coisa melhor.", CYAN))
        print(linha_pontilhada())

        lista_receitas = list(receitas.items())
        for indice, (_, receita) in enumerate(lista_receitas, 1):
            status = colorir("[PRONTO]", GREEN) if receita_disponivel(player, receita) else colorir("[FALTANDO]", RED)
            print(f"[{indice}] {receita.get('name', 'Melhoria')} {status}")
            _exibir_requisitos_receita(player, receita)
            print(linha_pontilhada())

        voltar = len(lista_receitas) + 1
        print(f"[{voltar}] Voltar")
        escolha = obter_entrada(
            "Escolha uma melhoria: ",
            opcoes=list(range(1, len(lista_receitas) + 2)),
        ) - 1

        if escolha == len(lista_receitas):
            return

        recipe_id, receita = lista_receitas[escolha]
        if not receita_disponivel(player, receita):
            print("\n" + fala_entidade(vendedor, "Ainda falta coisa nessa conta. Forja nao faz milagre de bolso vazio.", RED))
            print(pensamento_personagem(player.get("name", "Voce"), "Melhor conferir a mochila antes de insistir no martelo.", RED))
            aguardar_enter()
            continue

        resposta = obter_entrada(
            f"Melhorar para {_nome_item_por_id(receita.get('result_item'))}? (S/N): ",
            tipo=str,
        ).strip().lower()
        if resposta != "s":
            print(pensamento_personagem(player.get("name", "Voce"), "Ainda nao. Metal bom tambem espera a hora certa.", CYAN))
            aguardar_enter()
            continue

        resultado = melhorar_equipamento(player, recipe_id, local_id, "forge")
        if resultado.get("sucesso"):
            item_resultado = resultado.get("item_resultado", {})
            print("\n" + caixa_texto("EQUIPAMENTO MELHORADO", cor=GREEN))
            print(fala_entidade(vendedor, "Pronto. Agora isso tem peso de ferramenta seria.", GREEN))
            print(pensamento_personagem(player.get("name", "Voce"), f"{item_resultado.get('name', 'Item')} parece outro nas minhas maos.", GREEN))
        else:
            print("\n" + fala_entidade(vendedor, resultado.get("mensagem", "Algo deu errado na forja."), RED))
        aguardar_enter()


def _exibir_requisitos_grau(player, item):
    avaliacao = avaliar_aprimoramento_grau(player, item)
    if not avaliacao.get("upgradeable"):
        print(colorir(avaliacao.get("mensagem", "Este item nao pode ser aprimorado."), RED))
        return

    print(f"Grau: {avaliacao['grade']}/{avaliacao['max_grade']} -> {avaliacao['next_grade']}/{avaliacao['max_grade']}")
    print(
        f"Ouro: {avaliacao['gold_current']}/{avaliacao['gold_required']}G "
        f"- {_simbolo_requisito(avaliacao['gold_ok'])}"
    )
    print("Materiais:")
    for material_id, dados in avaliacao.get("materials", {}).items():
        print(
            f"  - {_nome_item_por_id(material_id)}: "
            f"{dados['current']}/{dados['required']} - {_simbolo_requisito(dados['ok'])}"
        )


def _aprimorar_grau_na_forja(player, vendedor):
    while True:
        limpar_tela()
        itens = listar_itens_aprimoraveis_grau(player)
        print(caixa_texto("APRIMORAR GRAU", cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player.get('gold', 0)) + 'G', YELLOW)}")
        print(fala_entidade(vendedor, "Grau nao troca a alma do item. So tira mais dela no martelo.", CYAN))
        print(linha_pontilhada())

        if not itens:
            print(fala_entidade(vendedor, "Nao vejo nada ai que aceite grau agora.", RED))
            aguardar_enter()
            return

        for indice, entrada in enumerate(itens, 1):
            item = entrada["item"]
            origem = "equipado" if entrada["origin"] == "equipped" else "mochila"
            status = colorir("[PRONTO]", GREEN) if aprimoramento_grau_disponivel(player, item) else colorir("[FALTANDO]", RED)
            print(f"[{indice}] {formatar_nome_com_grau(item)} ({origem}) {status}")
            _exibir_requisitos_grau(player, item)
            print(linha_pontilhada())

        voltar = len(itens) + 1
        print(f"[{voltar}] Voltar")
        escolha = obter_entrada(
            "Escolha um item: ",
            opcoes=list(range(1, len(itens) + 2)),
        ) - 1

        if escolha == len(itens):
            return

        item = itens[escolha]["item"]
        if not aprimoramento_grau_disponivel(player, item):
            print("\n" + fala_entidade(vendedor, "Sem material e ouro, isso aqui vira so barulho caro.", RED))
            aguardar_enter()
            continue

        avaliacao = avaliar_aprimoramento_grau(player, item)
        resposta = obter_entrada(
            f"Aprimorar {formatar_nome_com_grau(item)} para Grau {avaliacao['next_grade']}? (S/N): ",
            tipo=str,
        ).strip().lower()
        if resposta != "s":
            print(pensamento_personagem(player.get("name", "Voce"), "Ainda nao. Esse golpe de martelo pode esperar.", CYAN))
            aguardar_enter()
            continue

        resultado = aprimorar_grau_item(player, item)
        if resultado.get("sucesso"):
            print("\n" + caixa_texto("GRAU APRIMORADO", cor=GREEN))
            print(fala_entidade(vendedor, "Pronto. O mesmo item, so que menos humilde.", GREEN))
            print(pensamento_personagem(player.get("name", "Voce"), f"{formatar_nome_com_grau(item)} parece responder melhor na mao.", GREEN))
        else:
            print("\n" + fala_entidade(vendedor, resultado.get("mensagem", "Algo deu errado no aprimoramento."), RED))
        aguardar_enter()


def _comprar_item_na_barraca(player, itens_disponiveis, vendedor, dialogos, local_id, loja_id):
    while True:
        limpar_tela()
        desconto = calcular_desconto_carisma(player)
        print(caixa_texto("MERCADORIAS", cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player['gold']) + 'G', YELLOW)}")
        if desconto > 0:
            print(colorir(f"Desconto por Carisma: {int(round(desconto * 100))}%", MAGENTA))
        print(linha_pontilhada())

        lista_itens = list(itens_disponiveis.items())

        for i, (_, item_info) in enumerate(lista_itens, 1):
            mods = _formatar_modificadores(item_info)
            preco_base = item_info["price"]
            preco_final = calcular_preco_final(player, item_info)
            preco_texto = colorir(f"{preco_final}G", YELLOW)
            if preco_final != preco_base:
                preco_texto = f"{colorir(str(preco_final) + 'G', YELLOW)} (base {preco_base}G)"
            bloqueado = ""
            if player.get("level", 1) < item_info.get("level_required", 1):
                bloqueado = colorir(" [NIVEL PARA EQUIPAR]", YELLOW)
            print(f"[{i}] {item_info['name']} - {preco_texto} ({_formatar_meta_item(item_info)} | {mods}){bloqueado}")

        print(f"[{len(lista_itens) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha o que comprar: ",
            opcoes=list(range(1, len(lista_itens) + 2)),
        ) - 1

        if escolha == len(lista_itens):
            break

        item_chave, item_dados = lista_itens[escolha]

        if tentar_comprar_item(player, item_chave, item_dados):
            registrar_compra_loja(player, local_id, loja_id)
            print("\n" + fala_entidade(vendedor, dialogos["sucesso_compra"], GREEN))
            print(pensamento_personagem(player.get("name", "Voce"), f"{item_dados['name']} agora e meu. Que valha o ouro.", GREEN))
            item_comprado = player.get("inventory", [])[-1] if player.get("inventory") else None
            if player.get("level", 1) < item_dados.get("level_required", 1):
                _exibir_aviso_item_acima_do_nivel(player, vendedor, dialogos, item_dados)
            if item_comprado:
                _perguntar_equipar_item(player, item_comprado)
            else:
                aguardar_enter()
        else:
            print("\n" + fala_entidade(vendedor, dialogos["sem_ouro"], RED))
            aguardar_enter()


def _vender_item_na_barraca(player, vendedor):
    while True:
        limpar_tela()
        itens_vendiveis = listar_itens_vendiveis(player)
        print(caixa_texto("VENDER ITENS", cor=MAGENTA))
        print(f"Seu Ouro: {colorir(str(player['gold']) + 'G', YELLOW)}")
        print(linha_pontilhada())

        if not itens_vendiveis:
            print(fala_entidade(vendedor, "Nao vejo nada ai que eu possa comprar agora."))
            aguardar_enter()
            return

        for i, item in enumerate(itens_vendiveis, 1):
            valor = calcular_valor_venda(item)
            print(
                f"[{i}] {formatar_nome_com_quantidade(item)} "
                f"- vender por {colorir(str(valor) + 'G', YELLOW)} cada "
                f"({_formatar_item_venda(item)})"
            )

        print(f"[{len(itens_vendiveis) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha o que vender: ",
            opcoes=list(range(1, len(itens_vendiveis) + 2)),
        ) - 1

        if escolha == len(itens_vendiveis):
            return

        item = itens_vendiveis[escolha]
        quantidade = _escolher_quantidade_venda(item)
        if quantidade <= 0:
            continue

        nome_item = item.get("name", "Item")
        resultado = vender_item(player, item, quantidade)
        if resultado.get("sucesso"):
            quantidade_vendida = resultado.get("quantidade", quantidade)
            sufixo = f" x{quantidade_vendida}" if quantidade_vendida > 1 else ""
            print(pensamento_personagem(player.get("name", "Voce"), f"{nome_item}{sufixo} virou {resultado['valor']}G. A mochila agradece.", GREEN))
        else:
            print(pensamento_personagem(player.get("name", "Voce"), resultado.get("mensagem", "Esse item nao vai sair da minha mao tao facil."), RED))
        aguardar_enter()
