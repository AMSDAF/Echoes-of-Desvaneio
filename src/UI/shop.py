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
from src.services.event_service import resolver_evento_urbano
from src.services.item_service import equipar_item, formatar_propriedades_item
from src.services.shop_service import (
    calcular_desconto_carisma,
    calcular_preco_final,
    calcular_valor_venda,
    jogador_tem_item_raro,
    jogador_tem_itens_no_inventario,
    listar_itens_vendiveis,
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
    if item.get("type") == "material":
        return "material"

    mods = _formatar_modificadores(item)
    durabilidade = ""
    if item.get("slot") not in {"consumable", "potion", None}:
        durabilidade_atual = item.get("current_durability", item.get("durability", 100))
        durabilidade_maxima = item.get("max_durability", 100)
        durabilidade = f" | Durabilidade: {durabilidade_atual}/{durabilidade_maxima}"

    return f"{item.get('slot', 'item')} | {mods}{durabilidade}"


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


def _exibir_dialogo_inicial(player, vendedor, dialogos):
    if jogador_tem_item_raro(player):
        print(f"{vendedor}: \"{dialogos['inveja']}\"")
    elif jogador_tem_itens_no_inventario(player):
        print(f"{vendedor}: \"{dialogos['retorno']}\"")
    else:
        print(f"{vendedor}: \"{dialogos['primeira_vez']}\"")


def _perguntar_equipar_item(player, item):
    if item.get("slot") == "consumable":
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
            abrir_barraca(player, itens, loja_escolhida)
        else:
            print("\n" + pensamento_personagem(player.get("name", "Voce"), "Estou olhando para o lugar errado.", RED))


def abrir_barraca(player, itens_disponiveis, dados_loja):
    nome_da_barraca = dados_loja["nome"]
    vendedor = dados_loja["vendedor"]
    dialogos = dados_loja["dialogos"]

    print(caixa_texto(f"Ao se aproximar de: {nome_da_barraca.upper()}", cor=MAGENTA))
    _exibir_dialogo_inicial(player, vendedor, dialogos)

    aguardar_enter("\nPressione Enter para ver as mercadorias...")

    while True:
        limpar_tela()
        print(caixa_texto(nome_da_barraca.upper(), cor=YELLOW))
        print(f"Seu Ouro: {colorir(str(player['gold']) + 'G', YELLOW)}")
        print(linha_pontilhada())
        print("[1] Comprar")
        print("[2] Vender Itens")
        print("[3] Conversar / Procurar Rumores")
        print("[4] Voltar")
        print(linha_pontilhada())

        acao_loja = obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3, 4])
        if acao_loja == 1:
            _comprar_item_na_barraca(player, itens_disponiveis, vendedor, dialogos)
        elif acao_loja == 2:
            _vender_item_na_barraca(player, vendedor)
        elif acao_loja == 3:
            _exibir_evento_mercado(player)
            aguardar_enter()
        else:
            break


def _comprar_item_na_barraca(player, itens_disponiveis, vendedor, dialogos):
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
                bloqueado = colorir(" [NIVEL INSUFICIENTE]", RED)
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
            print("\n" + fala_entidade(vendedor, dialogos["sucesso_compra"], GREEN))
            print(pensamento_personagem(player.get("name", "Voce"), f"{item_dados['name']} agora e meu. Que valha o ouro.", GREEN))
            item_comprado = player.get("inventory", [])[-1] if player.get("inventory") else None
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
                f"[{i}] {item.get('name', 'Item desconhecido')} "
                f"- vender por {colorir(str(valor) + 'G', YELLOW)} "
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
        resultado = vender_item(player, item)
        if resultado.get("sucesso"):
            print(pensamento_personagem(player.get("name", "Voce"), f"{item.get('name', 'Item')} virou {resultado['valor']}G. A mochila agradece.", GREEN))
        else:
            print(pensamento_personagem(player.get("name", "Voce"), "Esse item nao vai sair da minha mao tao facil.", RED))
        aguardar_enter()
