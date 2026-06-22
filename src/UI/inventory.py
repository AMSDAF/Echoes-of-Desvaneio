import random

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
from src.services.attribute_service import ATRIBUTOS_LEGADOS, NOMES_ATRIBUTOS
from src.services.combat_service import calcular_custo_habilidade
from src.services.item_service import (
    calcular_atributos_totais,
    consolidar_itens_empilhaveis,
    consumir_pocao,
    equipar_item,
    formatar_nome_com_grau,
    formatar_propriedades_item,
    item_e_empilhavel,
    obter_quantidade_item,
    obter_razao_durabilidade,
)
from src.services.item_catalog_service import normalizar_slot_item
from src.services.condition_service import obter_nome_condicao
from src.services.level_service import garantir_estrutura_evolucao, gastar_ponto_atributo, xp_para_proximo_level
from src.services.skill_service import (
    calcular_custo_treino_habilidade,
    listar_habilidades_conhecidas_detalhadas,
    treinar_habilidade,
)


CATEGORIAS_MOCHILA = {
    "1": {
        "nome": "Armas",
        "slots": ["weapon"],
    },
    "2": {
        "nome": "Armaduras (Elmo, Peitoral, Calca, Bota)",
        "slots": ["helmet", "breastplate", "pants", "boots"],
    },
    "3": {
        "nome": "Escudos",
        "slots": ["shield"],
    },
    "4": {
        "nome": "Acessorios (Anel, Colar)",
        "slots": ["ring", "necklace"],
    },
    "5": {
        "nome": "Pocoes / Consumiveis",
        "slots": ["potion", "consumable"],
    },
    "6": {
        "nome": "Materiais / Tesouros",
        "categories": ["material", "valuable", "quest", "special"],
    },
}

NOMES_SLOTS = {
    "helmet": "Elmo",
    "breastplate": "Peitoral",
    "pants": "Calca",
    "boots": "Botas",
    "shield": "Escudo",
    "ring": "Anel",
    "necklace": "Colar",
    "weapon": "Arma",
}


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

    if item.get("remove_condition"):
        return f"Remove {obter_nome_condicao(item['remove_condition'])}"

    if item.get("applies_condition"):
        condicao = item["applies_condition"]
        return f"Aplica {obter_nome_condicao(condicao.get('id'))} ({condicao.get('duration', 1)}t)"

    modifiers = item.get("modifiers", {})
    propriedades = formatar_propriedades_item(item)
    if not modifiers and not propriedades:
        return "sem modificadores"

    nomes = {
        "hp_restore": "Vida",
        "defense": "Defesa",
    }

    partes = []
    for attr, val in modifiers.items():
        attr = ATRIBUTOS_LEGADOS.get(attr, attr)
        sinal = "+" if val >= 0 else ""
        partes.append(f"{nomes.get(attr, NOMES_ATRIBUTOS.get(attr, attr.capitalize()))} {sinal}{val}")

    partes.extend(propriedades)
    return ", ".join(partes)


def _item_esta_equipado(player, item):
    slot = normalizar_slot_item(item)
    item_equipado = player.get("equipped", {}).get(slot)
    return item_equipado is item or item_equipado == item


def _formatar_durabilidade(item):
    if item.get("slot") in {"potion", "consumable"}:
        return ""

    durabilidade = item.get("durability", 100)
    durabilidade_maxima = item.get("max_durability", 100)
    return f" | Durabilidade: [{durabilidade}/{durabilidade_maxima}]"


def _formatar_meta_item(item):
    if item.get("slot") in {"potion", "consumable"}:
        return ""

    if item.get("category") in {"material", "valuable", "quest", "special"} or item.get("type") in {"material", "valuable", "quest", "special"}:
        raridade = item.get("rarity", "common")
        categoria = item.get("category", item.get("type", "item"))
        return f" | {categoria} | {raridade}"

    nivel = item.get("level_required", 1)
    raridade = item.get("rarity", "comum")
    return f" | Nv. {nivel} | {raridade}"


def _durabilidade_baixa(item):
    if item.get("slot") in {"potion", "consumable"}:
        return False

    return obter_razao_durabilidade(item) < 0.3


def _descrever_efeitos_pocao(efeitos):
    nomes = {
        "hp_restore": "Vida",
        "mana_restore": "Mana",
        "stamina_restore": "Estamina",
        "defense": "defesa",
        "condition_removed": "Removeu",
        "condition_applied": "Aplicou",
    }

    descricoes = []
    for attr, val in efeitos:
        attr = ATRIBUTOS_LEGADOS.get(attr, attr)
        if val == 0:
            continue

        if attr in {"condition_removed", "condition_applied"}:
            descricoes.append(f"{nomes[attr]} {val}")
            continue

        sinal = "+" if val > 0 else ""
        descricoes.append(f"{nomes.get(attr, NOMES_ATRIBUTOS.get(attr, attr))} {sinal}{val}")

    return ", ".join(descricoes)


def _cor_efeito_pocao(efeitos):
    for attr, _ in efeitos:
        if attr == "mana_restore":
            return BLUE
        if attr == "stamina_restore":
            return CYAN
        if attr == "hp_restore":
            return GREEN
        if attr in {"condition_removed", "condition_applied"}:
            return MAGENTA
    return GREEN


def _formatar_nome_inventario(item):
    nome = formatar_nome_com_grau(item)
    quantidade = obter_quantidade_item(item)
    if item_e_empilhavel(item) or quantidade > 1:
        return f"{nome} | Quantidade: {quantidade}"
    return nome


def _exibir_resultado_pocao(player, item, efeitos):
    nome_hero = player.get("name", "Voce")
    descricao_efeitos = _descrever_efeitos_pocao(efeitos)
    cor = _cor_efeito_pocao(efeitos)

    limpar_tela()
    print(caixa_texto("EFEITO DA POCAO", cor=cor))
    print(f"Item usado: {colorir(item.get('name', 'Pocao'), YELLOW)}")
    print(linha_pontilhada())

    if descricao_efeitos:
        print(colorir(f"Efeito aplicado: {descricao_efeitos}.", cor))
    else:
        print(colorir("Nenhum efeito perceptivel foi aplicado.", RED))

    print(linha_pontilhada())
    print(f"Vida: {colorir(str(player.get('current_hp', 0)) + '/' + str(player.get('max_hp', 0)), GREEN)}")
    print(f"Mana: {colorir(str(player.get('current_mana', 0)) + '/' + str(player.get('max_mana', 0)), BLUE)}")
    print(f"Estamina: {colorir(str(player.get('current_stamina', 0)) + '/' + str(player.get('max_stamina', 0)), CYAN)}")
    print(linha_pontilhada())
    if descricao_efeitos:
        print(pensamento_personagem(nome_hero, "Gosto horrivel... mas funcionou. Meu corpo entendeu antes da minha lingua.", cor))
    else:
        print(pensamento_personagem(nome_hero, "Nada. Ou isso era fraco demais, ou eu esperei milagre de garrafa errada.", RED))


def _filtrar_itens_categoria(player, categoria):
    slots_alvo = categoria.get("slots", [])
    categorias_alvo = categoria.get("categories", [])
    return [
        item for item in player.get("inventory", [])
        if normalizar_slot_item(item) in slots_alvo or item.get("category") in categorias_alvo or item.get("type") in categorias_alvo
    ]


def _exibir_equipamentos_atuais(player):
    print(caixa_texto("EQUIPAMENTOS ATUAIS", cor=YELLOW))
    equipados = player.get("equipped", {})

    for slot, nome_slot in NOMES_SLOTS.items():
        item = equipados.get(slot)
        if not item:
            print(f"- {nome_slot}: {colorir('vazio', MAGENTA)}")
            continue

        durabilidade = _formatar_durabilidade(item)
        print(
            f"- {nome_slot}: {colorir(formatar_nome_com_grau(item), GREEN)} "
            f"({_formatar_modificadores(item)}){_formatar_meta_item(item)}{durabilidade}"
        )


def _gastar_pontos_atributo(player):
    attr_keys = list(NOMES_ATRIBUTOS.keys())

    while True:
        limpar_tela()
        pontos = player.get("attribute_points", 0)
        print(caixa_texto("APRIMORAR ATRIBUTOS", cor=GREEN))
        print(f"Pontos disponiveis: {colorir(pontos, YELLOW)}")
        print(linha_pontilhada())

        atributos = player.get("attributes", {})
        for i, attr in enumerate(attr_keys, 1):
            print(f"[{i}] {NOMES_ATRIBUTOS.get(attr, attr)}: {atributos.get(attr, 0)}")
        print(f"[{len(attr_keys) + 1}] Voltar")
        print(linha_pontilhada())

        if pontos <= 0:
            print(pensamento_personagem(player.get("name", "Voce"), "Nao adianta forcar crescimento que ainda nao conquistei.", CYAN))
            aguardar_enter()
            return

        escolha = obter_entrada(
            "Escolha o atributo para melhorar: ",
            opcoes=list(range(1, len(attr_keys) + 2)),
        ) - 1

        if escolha == len(attr_keys):
            return

        atributo = attr_keys[escolha]
        resultado = gastar_ponto_atributo(player, atributo)
        cor = GREEN if resultado.get("sucesso") else RED
        print(colorir(resultado.get("mensagem", "Acao concluida."), cor))
        if resultado.get("sucesso"):
            print(colorir(f"{NOMES_ATRIBUTOS[atributo]} aumentou para {player['attributes'][atributo]}!", GREEN))
        aguardar_enter()


def _nome_recurso_skill(resource):
    nomes = {
        "mana": "Mana",
        "stamina": "Estamina",
        "hp": "Vida",
    }
    return nomes.get(resource, str(resource).capitalize())


def _cor_categoria_habilidade(categoria):
    return CYAN if categoria == "fisico" else BLUE


def _formatar_chance(valor):
    return f"{int(round(float(valor) * 100))}%"


def _formatar_condicao_habilidade(habilidade):
    condicao = habilidade.get("applies_condition")
    if not condicao:
        return "Nenhuma"

    nome = obter_nome_condicao(condicao.get("id"))
    partes = [
        nome,
        f"chance {_formatar_chance(condicao.get('chance', 0))}",
        f"{condicao.get('duration', 1)} turno(s)",
    ]
    save = condicao.get("save")
    if save:
        atributo = NOMES_ATRIBUTOS.get(save.get("attribute"), save.get("attribute", "atributo"))
        partes.append(f"resistencia {atributo} CD {save.get('dc', 10)}")
    return " | ".join(partes)


def _exibir_habilidade_detalhada(player, habilidade, indice):
    resource, value = calcular_custo_habilidade(player, habilidade)
    categoria = "Fisica" if habilidade.get("category") == "fisico" else "Magica"
    upgrades = habilidade.get("upgrade_count", 0)
    max_upgrades = habilidade.get("max_upgrades", 0)
    custo_treino = calcular_custo_treino_habilidade(player, habilidade)
    cor_categoria = _cor_categoria_habilidade(habilidade.get("category"))

    print(colorir(f"[{indice}] {habilidade.get('name', 'Habilidade desconhecida')}", cor_categoria))
    print(
        f"    {categoria} | Nv. {habilidade.get('skill_level', 1)} "
        f"({upgrades}/{max_upgrades} treinos) | {habilidade.get('rarity', 'comum')}"
    )
    print(
        f"    Custo: {value} {_nome_recurso_skill(resource)} | "
        f"Dano: x{habilidade.get('multiplier', 1)} | Requer nivel {habilidade.get('level_required', 1)}"
    )
    print(f"    Efeito: {_formatar_condicao_habilidade(habilidade)}")
    print(f"    Treinar: {custo_treino} ponto(s) de habilidade")
    print(f"    {habilidade.get('description', 'Sem descricao.')}")


def _exibir_habilidade_resumida(indice, habilidade):
    categoria = "Fisica" if habilidade.get("category") == "fisico" else "Magica"
    upgrades = habilidade.get("upgrade_count", 0)
    max_upgrades = habilidade.get("max_upgrades", 0)
    cor_categoria = _cor_categoria_habilidade(habilidade.get("category"))
    nome = habilidade.get("name", "Habilidade desconhecida")
    nivel = habilidade.get("skill_level", 1)
    raridade = habilidade.get("rarity", "comum")
    progresso = f"{upgrades}/{max_upgrades}"

    print(
        f"[{indice}] {colorir(nome, cor_categoria)} | "
        f"{categoria} | Nv. {nivel} | {raridade} | Treino {progresso}"
    )


def _gerenciar_habilidades(player):
    while True:
        garantir_estrutura_evolucao(player)
        limpar_tela()
        habilidades = listar_habilidades_conhecidas_detalhadas(player)
        print(caixa_texto("HABILIDADES E TREINO", cor=MAGENTA))
        print(f"Pontos de habilidade: {colorir(player.get('skill_points', 0), YELLOW)}")
        print(linha_pontilhada())

        if not habilidades:
            print(pensamento_personagem(player.get("name", "Voce"), "Ainda nao tenho tecnicas para lapidar.", CYAN))
            aguardar_enter()
            return

        for i, habilidade in enumerate(habilidades, 1):
            _exibir_habilidade_resumida(i, habilidade)

        voltar = len(habilidades) + 1
        print(linha_pontilhada())
        print(f"[{voltar}] Voltar")
        escolha = obter_entrada(
            "Escolha uma habilidade para treinar/ver melhor: ",
            opcoes=list(range(1, len(habilidades) + 2)),
        ) - 1

        if escolha == len(habilidades):
            return

        habilidade = habilidades[escolha]
        limpar_tela()
        print(caixa_texto(habilidade.get("name", "HABILIDADE"), cor=_cor_categoria_habilidade(habilidade.get("category"))))
        _exibir_habilidade_detalhada(player, habilidade, 1)
        print(linha_pontilhada())
        print("[1] Treinar habilidade")
        print("[2] Voltar")
        acao = obter_entrada("Acao: ", opcoes=[1, 2])

        if acao == 2:
            continue

        resultado = treinar_habilidade(player, habilidade["id"])
        cor = GREEN if resultado.get("sucesso") else RED
        print("\n" + pensamento_personagem(player.get("name", "Voce"), resultado.get("mensagem", "Treino concluido."), cor))
        if resultado.get("sucesso"):
            habilidade_atualizada = resultado.get("habilidade", {})
            print(
                pensamento_personagem(
                    player.get("name", "Voce"),
                    f"Agora essa tecnica bate com x{habilidade_atualizada.get('multiplier', habilidade.get('multiplier', 1))}.",
                    YELLOW,
                )
            )
            print(
                pensamento_personagem(
                    player.get("name", "Voce"),
                    f"Ainda consigo treinar {player.get('skill_points', 0)} vez(es) antes de precisar viver mais um pouco.",
                    CYAN,
                )
            )
        aguardar_enter()


def exibir_status_e_inventario(player):
    nome_hero = player["name"]

    while True:
        garantir_estrutura_evolucao(player)
        limpar_tela()
        atributos_finais = calcular_atributos_totais(player)

        print(caixa_texto(f"FICHA DE PERSONAGEM: {nome_hero.upper()}", cor=CYAN))
        print(f" Classe: {player.get('class', 'Aventureiro')} | Nivel: {player.get('level', 1)}")
        print(f" Raca: {player.get('race', 'Desconhecida')} | XP: {player.get('xp', 0)}/{xp_para_proximo_level(player.get('level', 1))}")
        print(f" Pontos de Atributo: {colorir(player.get('attribute_points', 0), YELLOW)}")
        print(f" Pontos de Habilidade: {colorir(player.get('skill_points', 0), YELLOW)}")
        print(f" Vida: {colorir(str(player.get('current_hp', 100)) + '/' + str(player.get('max_hp', 100)), GREEN)}")
        print(f" Mana: {colorir(str(player.get('current_mana', 0)) + '/' + str(player.get('max_mana', 0)), BLUE)}")
        print(f" Estamina: {colorir(str(player.get('current_stamina', 0)) + '/' + str(player.get('max_stamina', 0)), CYAN)}")
        print(f" Ouro: {colorir(str(player['gold']) + 'G', YELLOW)} | Local: {player.get('current_location', 'phandalin').upper()}")
        print(linha_pontilhada())
        print(" Atributos Totais (Com Equipamentos):")

        for attr, val in atributos_finais.items():
            print(f"  - {NOMES_ATRIBUTOS.get(attr, attr.capitalize())}: {val}")

        print(linha_pontilhada())

        pensamentos = [
            f"{nome_hero} pensa: 'Aqueles goblins na Fenda dos Ratos vao pagar caro pelo que fizeram...'",
            f"{nome_hero} pensa: 'Sera que o velho Barthen aceitaria fiado se eu insistisse muito?'",
            f"{nome_hero} pensa: 'Sinto que meus musculos estao mudando, mas preciso de aco melhor...'",
        ]
        print(random.choice(pensamentos))
        print(linha_pontilhada())
        print("[1] Abrir Mochila (Equipar / Usar Itens)")
        print("[2] Aprimorar Atributos")
        print("[3] Ver / Treinar Habilidades")
        print("[4] Voltar para a Vila")
        print(linha_pontilhada())

        escolha = str(obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3, 4]))

        if escolha == "1":
            gerenciar_mochila(player)
        elif escolha == "2":
            _gastar_pontos_atributo(player)
        elif escolha == "3":
            _gerenciar_habilidades(player)
        elif escolha == "4":
            break
        else:
            print(f"\n{nome_hero} limpa os olhos: 'Acho que estou meio cansado... o que eu estava tentando selecionar mesmo?'")


def gerenciar_mochila(player):
    nome_hero = player["name"]
    calcular_atributos_totais(player)
    consolidar_itens_empilhaveis(player)

    while True:
        limpar_tela()
        _exibir_equipamentos_atuais(player)
        print(linha_pontilhada())
        print(caixa_texto("MOCHILA", cor=MAGENTA))
        for opcao, categoria in CATEGORIAS_MOCHILA.items():
            print(f"[{opcao}] {categoria['nome']}")
        opcao_voltar = str(len(CATEGORIAS_MOCHILA) + 1)
        print(f"[{opcao_voltar}] Voltar")
        print(linha_pontilhada())

        cat = str(obter_entrada(
            "Escolha uma categoria para olhar: ",
            opcoes=list(range(1, len(CATEGORIAS_MOCHILA) + 2)),
        ))

        if cat == opcao_voltar:
            break

        categoria = CATEGORIAS_MOCHILA.get(cat)
        if not categoria:
            print(f"\n{nome_hero} hesita: 'Minha cabeca esta voando... essa opcao nem faz sentido.'")
            continue

        itens_filtrados = _filtrar_itens_categoria(player, categoria)

        if not itens_filtrados:
            print(f"\n{nome_hero} vasculha a mochila: \"O que estou procurando? Eu nao tenho essas coisas aqui... melhor olhar outro bolso.\"")
            aguardar_enter()
            continue

        print(caixa_texto("ITENS NA MOCHILA", cor=CYAN))
        for i, item in enumerate(itens_filtrados, 1):
            slot_do_item = normalizar_slot_item(item) or item.get("category") or item.get("type") or "desconhecido"
            status_equipado = " [EQUIPADO]" if _item_esta_equipado(player, item) else ""
            durabilidade = _formatar_durabilidade(item)

            print(f"[{i}] {_formatar_nome_inventario(item)} ({slot_do_item.upper()}) ({_formatar_modificadores(item)}){_formatar_meta_item(item)}{status_equipado}{durabilidade}")

        print(f"[{len(itens_filtrados) + 1}] Voltar")

        op_item = obter_entrada(
            "\nEscolha um item para interagir (ou voltar): ",
            opcoes=list(range(1, len(itens_filtrados) + 2)),
        ) - 1
        if op_item == len(itens_filtrados):
            continue

        item_chosen = itens_filtrados[op_item]
        slot_do_item = normalizar_slot_item(item_chosen)
        item_interativo = slot_do_item in {"potion", "consumable"} or slot_do_item in NOMES_SLOTS

        if not item_interativo:
            print("\n" + caixa_texto(item_chosen.get("name", "ITEM"), cor=YELLOW))
            print(item_chosen.get("description", "Sem descricao."))
            print(f"Raridade: {item_chosen.get('rarity', 'common')} | Categoria: {item_chosen.get('category', item_chosen.get('type', 'item'))}")
            print(f"Valor de venda: {colorir(str(item_chosen.get('sell_price', 0)) + 'G', YELLOW)}")
            print(pensamento_personagem(nome_hero, "Melhor guardar isso. Algum mercador ou artesao pode querer depois.", CYAN))
            aguardar_enter()
            continue

        if slot_do_item not in {"potion", "consumable"}:
            print("\nVoce olha para o item com cuidado...")
            if _durabilidade_baixa(item_chosen):
                print(colorir(f"{nome_hero}: \"Esse item esta nas ultimas... se eu nao consertar ou trocar logo, vai me deixar na mao em combate.\"", RED))
            else:
                print(colorir(f"{nome_hero}: \"Boa escolha. Esse equipamento ainda esta em excelente estado.\"", GREEN))
            if player.get("level", 1) < item_chosen.get("level_required", 1):
                print(
                    pensamento_personagem(
                        nome_hero,
                        f"Esse equipamento pede nivel {item_chosen.get('level_required', 1)}. Ainda nao e a minha hora.",
                        YELLOW,
                    )
                )
            print("[1] Equipar isso agora")
        else:
            print("\n[1] Consumir isso agora")

        print("[2] Cancelar")

        acao = str(obter_entrada("Acao: ", opcoes=[1, 2]))
        if acao == "1":
            if slot_do_item not in {"potion", "consumable"}:
                if player.get("level", 1) < item_chosen.get("level_required", 1):
                    print(
                        "\n" + pensamento_personagem(
                            nome_hero,
                            f"Tento ajustar {item_chosen.get('name', 'Item')}, mas meu corpo ainda nao acompanha. Preciso de nivel {item_chosen.get('level_required', 1)}.",
                            RED,
                        )
                    )
                elif equipar_item(player, item_chosen):
                    print("\n" + pensamento_personagem(nome_hero, f"{item_chosen.get('name', 'Item')} encaixa bem. Que aguente o proximo problema.", GREEN))
                else:
                    print(colorir(f"\n{nome_hero} franze a testa: 'Nao faco ideia de onde eu colocaria isso.'", RED))
                aguardar_enter()
            else:
                efeitos = consumir_pocao(player, item_chosen)
                _exibir_resultado_pocao(player, item_chosen, efeitos)
                aguardar_enter()
