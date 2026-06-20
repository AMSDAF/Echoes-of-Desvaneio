from src.services.database import carregar_json
from src.services.shop_service import (
    jogador_tem_item_raro,
    jogador_tem_itens_no_inventario,
    tentar_comprar_item,
)


def _formatar_modificadores(item):
    modifiers = item.get("modifiers", {})
    if not modifiers:
        return "sem modificadores"

    partes = []
    for attr, val in modifiers.items():
        sinal = "+" if val >= 0 else ""
        partes.append(f"{attr.capitalize()} {sinal}{val}")

    return ", ".join(partes)


def _exibir_dialogo_inicial(player, vendedor, dialogos):
    if jogador_tem_item_raro(player):
        print(f"{vendedor}: \"{dialogos['inveja']}\"")
    elif jogador_tem_itens_no_inventario(player):
        print(f"{vendedor}: \"{dialogos['retorno']}\"")
    else:
        print(f"{vendedor}: \"{dialogos['primeira_vez']}\"")


def visitar_comercio(player):
    dados_comercio_geral = carregar_json("data/core/shops.json")

    local_atual = player.get("current_location", "phandalin")
    dados_da_vila = dados_comercio_geral[local_atual]
    lojas_da_vila = dados_da_vila["lojas"]

    while True:
        print(f"\n=== COMERCIO: {dados_da_vila['nome_exibicao']} ===")
        print(f"Seu Ouro: {player['gold']}G")
        print("--------------------------------")

        for opcao, dados_loja in lojas_da_vila.items():
            print(f"[{opcao}] {dados_loja['nome']}")

        opcao_sair = str(len(lojas_da_vila) + 1)
        print(f"[{opcao_sair}] Voltar para a Vila (Menu Principal)")
        print("--------------------------------")

        escolha = input("Onde deseja ir? ").strip()

        if escolha == opcao_sair:
            print("\nSaindo do comercio...")
            break
        elif escolha in lojas_da_vila:
            loja_escolhida = lojas_da_vila[escolha]
            itens = carregar_json(loja_escolhida["arquivo"])
            abrir_barraca(player, itens, loja_escolhida)
        else:
            print("\nOpcao invalida!")


def abrir_barraca(player, itens_disponiveis, dados_loja):
    nome_da_barraca = dados_loja["nome"]
    vendedor = dados_loja["vendedor"]
    dialogos = dados_loja["dialogos"]

    print(f"\n[Ao se aproximar de: {nome_da_barraca.upper()}]")
    _exibir_dialogo_inicial(player, vendedor, dialogos)

    input("\nPressione Enter para ver as mercadorias...")

    while True:
        print(f"\n--- {nome_da_barraca.upper()} ---")
        print(f"Seu Ouro: {player['gold']}G")
        print("--------------------------------")

        lista_itens = list(itens_disponiveis.items())

        for i, (_, item_info) in enumerate(lista_itens, 1):
            mods = _formatar_modificadores(item_info)
            print(f"[{i}] {item_info['name']} - {item_info['price']}G ({mods})")

        print(f"[{len(lista_itens) + 1}] Voltar")
        print("--------------------------------")

        try:
            escolha = int(input("Escolha o que comprar: ")) - 1

            if escolha == len(lista_itens):
                break

            if 0 <= escolha < len(lista_itens):
                item_chave, item_dados = lista_itens[escolha]

                if tentar_comprar_item(player, item_chave, item_dados):
                    print(f"\n{vendedor}: \"{dialogos['sucesso_compra']}\"")
                    print(f"Voce adquiriu: {item_dados['name']}!")
                    input("\nPressione Enter para continuar...")
                else:
                    print(f"\n{vendedor}: \"{dialogos['sem_ouro']}\"")
                    input("\nPressione Enter para continuar...")
            else:
                print("\nOpcao invalida!")
        except ValueError:
            print("\nPor favor, digite um numero valido.")
