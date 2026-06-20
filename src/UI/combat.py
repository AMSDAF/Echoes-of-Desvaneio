import random

from src.services.attribute_service import formatar_percentual
from src.services.combat_service import (
    calcular_chance_contra_ataque,
    calcular_chance_esquiva,
    calcular_chance_fuga,
    calcular_chance_critico,
    calcular_dano_habilidade,
    calcular_desgaste_arma,
    calcular_percentual_dano_bloqueio,
    carregar_dados_monstro,
    consumir_recurso_habilidade,
    jogador_tem_recurso_para_habilidade,
    listar_habilidades_conhecidas,
    obter_efeitos_raciais,
    processar_defesa,
    processar_vitoria,
)
from src.services.database import salvar_json
from src.services.item_service import calcular_atributos_totais
from src.services.level_service import garantir_estrutura_evolucao


def rodar_turno_defensivo_inimigo():
    """Sorteia a reacao do monstro ao ataque do jogador."""
    opcoes = ["esquivar", "bloquear", "contra_atacar"]
    return random.choices(opcoes, weights=[40, 40, 20])[0]


def _imprimir_opcoes_defesa(atributos_player, efeitos_raciais):
    chance_esquiva = calcular_chance_esquiva(atributos_player, efeitos_raciais)
    percentual_bloqueio = calcular_percentual_dano_bloqueio(atributos_player, efeitos_raciais)
    chance_contra_ataque = calcular_chance_contra_ataque(atributos_player, efeitos_raciais)

    print("Como voce vai se defender?")
    print(f"[1] Esquivar ({formatar_percentual(chance_esquiva)} chance - evita dano / falha recebe 50%)")
    print(f"[2] Bloquear (garantido - recebe {formatar_percentual(percentual_bloqueio)} do dano)")
    print(f"[3] Contra-Atacar ({formatar_percentual(chance_contra_ataque)} chance - causa 50% de dano / falha recebe +25%)")


def _monstro_ataca_livremente(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais):
    dano_punicao = max(1, dados_monstro["attack"])
    tipo_dano = dados_monstro.get("attack_type", "fisico")
    dano_punicao, _, _ = processar_defesa(
        dano_punicao,
        "sem_defesa",
        0,
        atributos_player,
        efeitos_raciais,
        tipo_dano,
    )
    player["current_hp"] = max(0, player["current_hp"] - dano_punicao)
    print(f"{nome_monstro} aproveita a abertura e causa {dano_punicao} de dano!")


def _nome_recurso(resource):
    nomes = {
        "mana": "Mana",
        "stamina": "Estamina",
    }
    return nomes.get(resource, resource.capitalize())


def _exibir_habilidade(indice, habilidade):
    cost = habilidade.get("cost", {})
    resource = cost.get("resource", "")
    value = cost.get("value", 0)
    print(
        f"[{indice}] {habilidade['name']} - "
        f"Custo: {value} {_nome_recurso(resource)} | "
        f"Multiplicador: x{habilidade.get('multiplier', 1)}"
    )
    print(f"    {habilidade.get('description', '')}")


def _escolher_habilidade(player, categoria):
    habilidades = listar_habilidades_conhecidas(player, categoria)
    if not habilidades:
        print("\nVoce ainda nao conhece habilidades dessa categoria.")
        input("Pressione Enter para voltar ao combate...")
        return None

    print("\n--- Habilidades Disponiveis ---")
    for i, habilidade in enumerate(habilidades, 1):
        _exibir_habilidade(i, habilidade)

    print(f"[{len(habilidades) + 1}] Voltar")

    try:
        escolha = int(input("Escolha a habilidade: ")) - 1
    except ValueError:
        print("\nOpcao invalida.")
        return None

    if escolha == len(habilidades):
        return None

    if 0 <= escolha < len(habilidades):
        return habilidades[escolha]

    print("\nOpcao invalida.")
    return None


def _selecionar_habilidade_de_ataque(player):
    print("\n--- Escolha sua Categoria de Habilidade ---")
    print("[1] Habilidades Fisicas")
    print("[2] Habilidades Magicas")
    print("[3] Voltar")
    sub_opcao = input(">> ").strip()

    if sub_opcao == "1":
        return "fisico", _escolher_habilidade(player, "fisico")

    if sub_opcao == "2":
        return "magia", _escolher_habilidade(player, "magico")

    return None, None


def combater(player, enemy_id, pode_fugir=True):
    if garantir_estrutura_evolucao(player):
        salvar_json("data/core/player.json", player)

    dados_monstro = carregar_dados_monstro(enemy_id)
    if not dados_monstro:
        print("\nErro: Criatura nao encontrada nas profundezas do codigo.")
        return False

    monstro_hp = dados_monstro["hp"]
    monstro_max_hp = dados_monstro["hp"]
    nome_monstro = dados_monstro["name"]
    efeitos_raciais = obter_efeitos_raciais(player)

    print("\n==============================================")
    print(f"       UM INIMIGO SE APROXIMA: {nome_monstro.upper()}")
    print("==============================================")

    while player["current_hp"] > 0 and monstro_hp > 0:
        atributos_player = calcular_atributos_totais(player)
        chance_fuga = calcular_chance_fuga(atributos_player, efeitos_raciais)

        print(f"\n[ {player['name']}: {player['current_hp']}/{player['max_hp']} HP ] VS [ {nome_monstro}: {monstro_hp}/{monstro_max_hp} HP ]")
        print("----------------------------------------------")
        print(f"Mana: {player.get('current_mana', 0)}/{player.get('max_mana', 0)} | Estamina: {player.get('current_stamina', 0)}/{player.get('max_stamina', 0)}")
        print("[1] Atacar")
        print("[2] Usar Item do Inventario")
        print(f"[3] Tentar Fugir ({formatar_percentual(chance_fuga)} chance)")
        print("----------------------------------------------")

        opcao = input("Escolha sua acao: ").strip()

        if opcao == "1":
            tipo_ataque, habilidade = _selecionar_habilidade_de_ataque(player)
            if not habilidade:
                continue

            if not jogador_tem_recurso_para_habilidade(player, habilidade):
                cost = habilidade.get("cost", {})
                print(
                    f"\nRecurso insuficiente: {habilidade['name']} exige "
                    f"{cost.get('value', 0)} {_nome_recurso(cost.get('resource', ''))}."
                )
                input("Pressione Enter para escolher outra acao...")
                continue

            consumir_recurso_habilidade(player, habilidade)
            dano_bruto = calcular_dano_habilidade(atributos_player, tipo_ataque, habilidade, efeitos_raciais)
            if random.random() <= calcular_chance_critico(efeitos_raciais):
                dano_bruto *= 2
                print("\nAcerto critico! O golpe encontra uma abertura perfeita.")
            calcular_desgaste_arma(player)
            print(f"\nVoce usa {habilidade['name']}!")

            postura_inimiga = rodar_turno_defensivo_inimigo()
            print(f"\n{nome_monstro} se prepara para: {postura_inimiga.upper()}!")

            dano_sofrido_inimigo, contra_dano, msg = processar_defesa(
                dano_bruto, postura_inimiga, dados_monstro["defense"]
            )

            monstro_hp = max(0, monstro_hp - dano_sofrido_inimigo)
            print(f"-> {msg}")
            if dano_sofrido_inimigo > 0:
                print(f"Voce causou {dano_sofrido_inimigo} de dano a {nome_monstro}.")

            if contra_dano > 0:
                player["current_hp"] = max(0, player["current_hp"] - contra_dano)
                print(f"Golpe de resposta! Voce sofreu {contra_dano} de dano do contra-ataque.")
                if player["current_hp"] <= 0:
                    break

            if monstro_hp <= 0:
                break

            print(f"\n--- Turno de {nome_monstro}! Ele avanca para desferir um golpe! ---")
            _imprimir_opcoes_defesa(atributos_player, efeitos_raciais)

            def_opcao = input("Escolha sua postura de defesa: ").strip()
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
            )

            player["current_hp"] = max(0, player["current_hp"] - dano_sofrido_player)
            print(f"\n-> {msg_player}")
            if dano_sofrido_player > 0:
                print(f"{nome_monstro} causou {dano_sofrido_player} de dano a voce.")

            if contra_dano_player > 0:
                monstro_hp = max(0, monstro_hp - contra_dano_player)
                print(f"Resposta de aco! Voce causou {contra_dano_player} de dano de volta.")

        elif opcao == "2":
            print("\n[Inventario Aberto] Voce mexe em suas bolsas... (Sistema de itens em desenvolvimento).")
            input("Pressione Enter para voltar ao combate...")

        elif opcao == "3":
            if not pode_fugir:
                print("\nIMPOSSIVEL FUGIR! O chefe bloqueia a sua rota de retirada.")
                input("Pressione Enter para voltar a luta...")
                continue

            if random.random() <= chance_fuga:
                print("\nVoce conseguiu escapar da batalha!")
                return False

            print("\nVoce tentou correr, mas o monstro ganhou uma abertura!")
            _monstro_ataca_livremente(player, dados_monstro, nome_monstro, atributos_player, efeitos_raciais)

        else:
            print("\nOpcao invalida! Concentre-se na luta!")

    if player["current_hp"] <= 0:
        print("\nVOCE CAIU EM COMBATE... As trevas do Desvaneio te consumiram.")
        player["current_hp"] = int(player["max_hp"] * 0.20)
        player["gold"] = max(0, player["gold"] - 20)
        salvar_json("data/core/player.json", player)
        return False

    print(f"\nVITORIA! {nome_monstro} desaba sem vida no chao.")
    materiais = processar_vitoria(player, dados_monstro)
    print(f"Recompensas: +{dados_monstro['xp_drop']} XP | +{dados_monstro['gold_drop']}G")
    if materiais:
        print(f"Materiais coletados para Craft: {', '.join(materiais)}")
    input("\nPressione Enter para coletar os espolios...")
    return True
