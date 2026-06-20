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
from src.services.item_service import (
    calcular_atributos_totais,
    consumir_pocao,
    equipar_item,
    formatar_propriedades_item,
    obter_razao_durabilidade,
)
from src.services.condition_service import obter_nome_condicao
from src.services.level_service import calcular_xp_necessario, gastar_ponto_atributo


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
        "nome": "Acessorios (Anel, Colar)",
        "slots": ["ring", "necklace"],
    },
    "4": {
        "nome": "Pocoes / Consumiveis",
        "slots": ["potion", "consumable"],
    },
}

NOMES_SLOTS = {
    "helmet": "Elmo",
    "breastplate": "Peitoral",
    "pants": "Calca",
    "boots": "Botas",
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
    slot = item.get("slot")
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

    nivel = item.get("level_required", 1)
    raridade = item.get("rarity", "comum")
    return f" | Nv. {nivel} | {raridade}"


def _durabilidade_baixa(item):
    if item.get("slot") in {"potion", "consumable"}:
        return False

    return obter_razao_durabilidade(item) < 0.3


def _descrever_efeitos_pocao(efeitos):
    nomes = {
        "hp_restore": "vida",
        "defense": "defesa",
        "condition_removed": "removeu",
        "condition_applied": "aplicou",
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
            f"- {nome_slot}: {colorir(item.get('name', 'Item desconhecido'), GREEN)} "
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


def exibir_status_e_inventario(player):
    nome_hero = player["name"]

    while True:
        limpar_tela()
        atributos_finais = calcular_atributos_totais(player)

        print(caixa_texto(f"FICHA DE PERSONAGEM: {nome_hero.upper()}", cor=CYAN))
        print(f" Classe: {player.get('class', 'Aventureiro')} | Nivel: {player.get('level', 1)}")
        print(f" Raca: {player.get('race', 'Desconhecida')} | XP: {player.get('xp', 0)}/{calcular_xp_necessario(player.get('level', 1))}")
        print(f" Pontos de Atributo: {colorir(player.get('attribute_points', 0), YELLOW)}")
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
        print("[3] Voltar para a Vila")
        print(linha_pontilhada())

        escolha = str(obter_entrada("O que deseja fazer? ", opcoes=[1, 2, 3]))

        if escolha == "1":
            gerenciar_mochila(player)
        elif escolha == "2":
            _gastar_pontos_atributo(player)
        elif escolha == "3":
            break
        else:
            print(f"\n{nome_hero} limpa os olhos: 'Acho que estou meio cansado... o que eu estava tentando selecionar mesmo?'")


def gerenciar_mochila(player):
    nome_hero = player["name"]

    while True:
        limpar_tela()
        _exibir_equipamentos_atuais(player)
        print(linha_pontilhada())
        print(caixa_texto("MOCHILA", cor=MAGENTA))
        for opcao, categoria in CATEGORIAS_MOCHILA.items():
            print(f"[{opcao}] {categoria['nome']}")
        print("[5] Voltar")
        print(linha_pontilhada())

        cat = str(obter_entrada("Escolha uma categoria para olhar: ", opcoes=[1, 2, 3, 4, 5]))

        if cat == "5":
            break

        categoria = CATEGORIAS_MOCHILA.get(cat)
        if not categoria:
            print(f"\n{nome_hero} hesita: 'Minha cabeca esta voando... essa opcao nem faz sentido.'")
            continue

        slots_alvo = categoria["slots"]
        itens_filtrados = [item for item in player.get("inventory", []) if item.get("slot") in slots_alvo]

        if not itens_filtrados:
            print(f"\n{nome_hero} vasculha a mochila: \"O que estou procurando? Eu nao tenho essas coisas aqui... melhor olhar outro bolso.\"")
            aguardar_enter()
            continue

        print(caixa_texto("ITENS NA MOCHILA", cor=CYAN))
        for i, item in enumerate(itens_filtrados, 1):
            slot_do_item = item.get("slot", "desconhecido")
            status_equipado = " [EQUIPADO]" if _item_esta_equipado(player, item) else ""
            durabilidade = _formatar_durabilidade(item)

            print(f"[{i}] {item['name']} ({slot_do_item.upper()}) ({_formatar_modificadores(item)}){_formatar_meta_item(item)}{status_equipado}{durabilidade}")

        print(f"[{len(itens_filtrados) + 1}] Voltar")

        op_item = obter_entrada(
            "\nEscolha um item para interagir (ou voltar): ",
            opcoes=list(range(1, len(itens_filtrados) + 2)),
        ) - 1
        if op_item == len(itens_filtrados):
            continue

        item_chosen = itens_filtrados[op_item]
        slot_do_item = item_chosen.get("slot")

        if slot_do_item not in {"potion", "consumable"}:
            print("\nVoce olha para o item com cuidado...")
            if _durabilidade_baixa(item_chosen):
                print(colorir(f"{nome_hero}: \"Esse item esta nas ultimas... se eu nao consertar ou trocar logo, vai me deixar na mao em combate.\"", RED))
            else:
                print(colorir(f"{nome_hero}: \"Boa escolha. Esse equipamento ainda esta em excelente estado.\"", GREEN))
            print("[1] Equipar isso agora")
        else:
            print("\n[1] Consumir isso agora")

        print("[2] Cancelar")

        acao = str(obter_entrada("Acao: ", opcoes=[1, 2]))
        if acao == "1":
            if slot_do_item not in {"potion", "consumable"}:
                if equipar_item(player, item_chosen):
                    print("\n" + pensamento_personagem(nome_hero, f"{item_chosen.get('name', 'Item')} encaixa bem. Que aguente o proximo problema.", GREEN))
                else:
                    print(colorir(f"\n{nome_hero} franze a testa: 'Nao faco ideia de onde eu colocaria isso.'", RED))
                aguardar_enter()
            else:
                efeitos = consumir_pocao(player, item_chosen)
                descricao_efeitos = _descrever_efeitos_pocao(efeitos)

                print("\nVoce toma a pocao...")
                if descricao_efeitos:
                    print(colorir(f"Efeito aplicado: {descricao_efeitos}.", GREEN))
                print(f"{nome_hero}: 'Gosto horrivel... mas sinto uma energia correndo pelas minhas veias de novo!'")
                aguardar_enter()
