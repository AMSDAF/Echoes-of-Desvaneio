from src.UI.utils.colors import (
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
from src.services.bestiary_service import listar_entradas_bestiario
from src.services.condition_service import obter_nome_condicao


def _formatar_percentual(valor):
    return f"{int(round(float(valor) * 100))}%"


def _nome_tipo_dano(enemy):
    tipo = enemy.get("attack_type", "fisico")
    return "Magico" if tipo == "magia" else "Fisico"


def _formatar_condicao(enemy):
    condicao = enemy.get("on_hit_condition")
    if not condicao:
        return "Nenhuma conhecida"

    partes = [
        obter_nome_condicao(condicao.get("id")),
        f"chance {_formatar_percentual(condicao.get('chance', 1))}",
        f"{condicao.get('duration', 1)}t",
    ]
    save = condicao.get("save")
    if save:
        partes.append(f"resiste com {save.get('attribute', 'atributo')} CD {save.get('dc', 10)}")

    return " | ".join(partes)


def _formatar_loot(enemy):
    loot = enemy.get("loot_table", [])
    if not loot:
        return ["Sem loot registrado"]

    return [
        f"- {item.get('item_id', 'item').replace('_', ' ').title()}: {_formatar_percentual(item.get('chance', 0))}"
        for item in loot
    ]


def _exibir_entrada(entrada, nome_heroi):
    enemy = entrada["enemy"]
    lore = entrada["lore"]
    state = entrada["state"]

    limpar_tela()
    print(caixa_texto(enemy.get("name", entrada["id"]).upper(), cor=RED))
    print(f"Categoria: {lore.get('category', 'Desconhecida')}")
    print(f"Habitat: {lore.get('habitat', 'Nao registrado')}")
    print(f"Encontrado: {state.get('seen', 0)} | Derrotado: {state.get('defeated', 0)}")
    print(linha_pontilhada())
    print(lore.get("lore", "Voce ainda sabe pouco sobre essa criatura."))

    if not entrada["mastered"]:
        print(linha_pontilhada(cor=MAGENTA))
        print(pensamento_personagem(nome_heroi, "Preciso derrubar uma dessas antes de confiar nas minhas anotacoes.", YELLOW))
        aguardar_enter()
        return

    print(linha_pontilhada(cor=MAGENTA))
    print(colorir("Estatisticas", CYAN))
    print(f"Nivel: {enemy.get('level', 1)}")
    print(f"HP: {enemy.get('hp', '?')} | Ataque: {enemy.get('attack', '?')} | Defesa: {enemy.get('defense', 0)}")
    print(f"Tipo de dano: {_nome_tipo_dano(enemy)} | Precisao: {_formatar_percentual(enemy.get('accuracy', 0))}")
    print(f"Condicao ao acertar: {_formatar_condicao(enemy)}")

    print(linha_pontilhada(cor=MAGENTA))
    print(colorir("Tatica", YELLOW))
    print(lore.get("tactics", "Sem anotacoes taticas."))
    print(colorir("Preparacao", GREEN))
    print(lore.get("preparation", "Sem preparo especial registrado."))

    print(linha_pontilhada(cor=MAGENTA))
    print(colorir("Loot Conhecido", CYAN))
    for linha in _formatar_loot(enemy):
        print(linha)

    aguardar_enter()


def exibir_bestiario(player):
    while True:
        limpar_tela()
        entradas = listar_entradas_bestiario(player)
        conhecidos = sum(1 for entrada in entradas if entrada["known"])
        dominados = sum(1 for entrada in entradas if entrada["mastered"])

        print(caixa_texto("BESTIARIO", cor=GREEN))
        print(f"Encontrados: {colorir(conhecidos, YELLOW)}/{len(entradas)} | Completos: {colorir(dominados, CYAN)}/{len(entradas)}")
        print(linha_pontilhada())

        for i, entrada in enumerate(entradas, 1):
            enemy = entrada["enemy"]
            if not entrada["known"]:
                print(f"[{i}] {colorir('???', MAGENTA)} - pagina vazia no diario")
                continue

            status = colorir("completo", GREEN) if entrada["mastered"] else colorir("avistado", YELLOW)
            print(f"[{i}] {enemy.get('name', entrada['id'])} - {status}")

        print(f"[{len(entradas) + 1}] Voltar")
        print(linha_pontilhada())

        escolha = obter_entrada(
            "Escolha uma entrada: ",
            opcoes=list(range(1, len(entradas) + 2)),
        ) - 1

        if escolha == len(entradas):
            return

        entrada = entradas[escolha]
        if not entrada["known"]:
            print("\n" + pensamento_personagem(player.get("name", "Voce"), "Ainda nao vi essa coisa com meus proprios olhos.", CYAN))
            aguardar_enter()
            continue

        _exibir_entrada(entrada, player.get("name", "Voce"))
