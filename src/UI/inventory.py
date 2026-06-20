import random

from src.services.item_service import (
    calcular_atributos_totais,
    consumir_pocao,
    equipar_item,
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
        "nome": "Acessorios (Anel, Colar)",
        "slots": ["ring", "necklace"],
    },
    "4": {
        "nome": "Pocoes / Consumiveis",
        "slots": ["potion"],
    },
}


def _formatar_modificadores(item):
    modifiers = item.get("modifiers", {})
    if not modifiers:
        return "sem modificadores"

    nomes = {
        "hp_restore": "Vida",
        "strength": "Forca",
        "agility": "Agilidade",
        "intelligence": "Inteligencia",
        "vitality": "Vitalidade",
        "defense": "Defesa",
    }

    partes = []
    for attr, val in modifiers.items():
        sinal = "+" if val >= 0 else ""
        partes.append(f"{nomes.get(attr, attr.capitalize())} {sinal}{val}")

    return ", ".join(partes)


def _item_esta_equipado(player, item):
    slot = item.get("slot")
    item_equipado = player.get("equipped", {}).get(slot)
    return item_equipado is item or item_equipado == item


def _formatar_durabilidade(item):
    if item.get("slot") == "potion":
        return ""

    durabilidade = item.get("durability", 100)
    durabilidade_maxima = item.get("max_durability", 100)
    return f" | Durabilidade: [{durabilidade}/{durabilidade_maxima}]"


def _durabilidade_baixa(item):
    if item.get("slot") == "potion":
        return False

    durabilidade = item.get("durability", 100)
    durabilidade_maxima = item.get("max_durability", 100)
    if durabilidade_maxima <= 0:
        return False

    return durabilidade / durabilidade_maxima < 0.3


def _descrever_efeitos_pocao(efeitos):
    nomes = {
        "hp_restore": "vida",
        "strength": "forca",
        "agility": "agilidade",
        "intelligence": "inteligencia",
        "vitality": "vitalidade",
        "defense": "defesa",
    }

    descricoes = []
    for attr, val in efeitos:
        if val == 0:
            continue

        sinal = "+" if val > 0 else ""
        descricoes.append(f"{nomes.get(attr, attr)} {sinal}{val}")

    return ", ".join(descricoes)


def exibir_status_e_inventario(player):
    nome_hero = player["name"]

    while True:
        atributos_finais = calcular_atributos_totais(player)

        print("\n==============================================")
        print(f"        FICHA DE PERSONAGEM: {nome_hero.upper()}        ")
        print("==============================================")
        print(f" Classe: {player.get('class', 'Aventureiro')} | Nivel: {player.get('level', 1)}")
        print(f" Vida: {player.get('current_hp', 100)}/{player.get('max_hp', 100)}")
        print(f" Ouro: {player['gold']}G | Local: {player.get('current_location', 'phandalin').upper()}")
        print("----------------------------------------------")
        print(" Atributos Totais (Com Equipamentos):")

        for attr, val in atributos_finais.items():
            print(f"  - {attr.capitalize()}: {val}")

        print("----------------------------------------------")

        pensamentos = [
            f"{nome_hero} pensa: 'Aqueles goblins na Fenda dos Ratos vao pagar caro pelo que fizeram...'",
            f"{nome_hero} pensa: 'Sera que o velho Barthen aceitaria fiado se eu insistisse muito?'",
            f"{nome_hero} pensa: 'Sinto que meus musculos estao mudando, mas preciso de aco melhor...'",
        ]
        print(random.choice(pensamentos))
        print("==============================================")
        print("[1] Abrir Mochila (Equipar / Usar Itens)")
        print("[2] Voltar para a Vila")
        print("----------------------------------------------")

        escolha = input("O que deseja fazer? ").strip()

        if escolha == "1":
            gerenciar_mochila(player)
        elif escolha == "2":
            break
        else:
            print(f"\n{nome_hero} limpa os olhos: 'Acho que estou meio cansado... o que eu estava tentando selecionar mesmo?'")


def gerenciar_mochila(player):
    nome_hero = player["name"]

    while True:
        print("\n--- MOCHILA ---")
        for opcao, categoria in CATEGORIAS_MOCHILA.items():
            print(f"[{opcao}] {categoria['nome']}")
        print("[5] Voltar")
        print("----------------")

        cat = input("Escolha uma categoria para olhar: ").strip()

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
            continue

        print("\n== RELEMBRANDO O QUE TENHO NA MOCHILA ==")
        for i, item in enumerate(itens_filtrados, 1):
            slot_do_item = item.get("slot", "desconhecido")
            status_equipado = " [EQUIPADO]" if _item_esta_equipado(player, item) else ""
            durabilidade = _formatar_durabilidade(item)

            print(f"[{i}] {item['name']} ({slot_do_item.upper()}) ({_formatar_modificadores(item)}){status_equipado}{durabilidade}")

        print(f"[{len(itens_filtrados) + 1}] Voltar")

        try:
            op_item = int(input("\nEscolha um item para interagir (ou voltar): ")) - 1
            if op_item == len(itens_filtrados):
                continue

            if 0 <= op_item < len(itens_filtrados):
                item_chosen = itens_filtrados[op_item]
                slot_do_item = item_chosen.get("slot")

                if slot_do_item != "potion":
                    print("\nVoce olha para o item com cuidado...")
                    if _durabilidade_baixa(item_chosen):
                        print(f"{nome_hero}: \"Esse item esta nas ultimas... se eu nao consertar ou trocar logo, vai me deixar na mao em combate.\"")
                    else:
                        print(f"{nome_hero}: \"Este aqui ainda quebra o galho, mas sinto que devo procurar algo novo logo... o desgaste esta vindo.\"")
                    print("[1] Equipar isso agora")
                else:
                    print("\n[1] Consumir isso agora")

                print("[2] Cancelar")

                acao = input("Acao: ").strip()
                if acao == "1":
                    if slot_do_item != "potion":
                        if equipar_item(player, item_chosen):
                            print(f"\nVoce equipa o item no slot {slot_do_item.upper()}...")
                            print(f"{nome_hero}: 'Isso aqui serve perfeitamente. Sinto que os atributos mudaram!'")
                        else:
                            print(f"\n{nome_hero} franze a testa: 'Nao faco ideia de onde eu colocaria isso.'")
                    else:
                        efeitos = consumir_pocao(player, item_chosen)
                        descricao_efeitos = _descrever_efeitos_pocao(efeitos)

                        print("\nVoce toma a pocao...")
                        if descricao_efeitos:
                            print(f"Efeito aplicado: {descricao_efeitos}.")
                        print(f"{nome_hero}: 'Gosto horrivel... mas sinto uma energia correndo pelas minhas veias de novo!'")
            else:
                print(f"\n{nome_hero} resmunga: 'Preciso escolher algo que esteja na minha frente.'")

        except ValueError:
            print(f"\n{nome_hero} resmunga: 'Minha cabeca esta fervendo... preciso digitar um numero valido.'")
