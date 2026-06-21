from src.UI.utils.colors import (
    CYAN,
    GREEN,
    MAGENTA,
    YELLOW,
    aguardar_enter,
    caixa_texto,
    colorir,
    linha_pontilhada,
    limpar_tela,
    pensamento_personagem,
)
from src.services.level_service import carregar_skills


def _nomes_skills(skill_ids):
    if not skill_ids:
        return []

    nomes = []
    dados_skills = carregar_skills()
    for skill_id in skill_ids:
        nome_encontrado = None
        for categoria in dados_skills.values():
            if skill_id in categoria:
                nome_encontrado = categoria[skill_id].get("name", skill_id)
                break
        nomes.append(nome_encontrado or skill_id.replace("_", " ").title())
    return nomes


def exibir_tela_level_up(player, resultado_xp):
    if not resultado_xp or resultado_xp.get("levels_ganhos", 0) <= 0:
        return

    nome = player.get("name", "Voce")
    limpar_tela()
    print(caixa_texto("LEVEL UP", cor=YELLOW))
    print(
        pensamento_personagem(
            nome,
            f"Algo em mim assentou no lugar. Eu nao sou mais o mesmo aventureiro de antes.",
            GREEN,
        )
    )
    print(linha_pontilhada(cor=MAGENTA))
    print(
        f"Nivel: {colorir(resultado_xp.get('nivel_anterior', '?'), CYAN)} "
        f"-> {colorir(resultado_xp.get('nivel_atual', player.get('level', '?')), GREEN)}"
    )
    print(f"XP atual: {colorir(resultado_xp.get('xp_atual', player.get('xp', 0)), YELLOW)}/{resultado_xp.get('xp_proximo', '?')}")
    print(f"Pontos de atributo ganhos: {colorir(resultado_xp.get('attribute_points_gained', 0), YELLOW)}")
    print(f"Pontos de habilidade ganhos: {colorir(resultado_xp.get('skill_points_gained', 0), YELLOW)}")

    novas_skills = _nomes_skills(resultado_xp.get("novas_skills", []))
    if novas_skills:
        print(linha_pontilhada(cor=MAGENTA))
        print(colorir("Novas habilidades desbloqueadas:", GREEN))
        for nome_skill in novas_skills:
            print(f"- {nome_skill}")

    print(linha_pontilhada(cor=MAGENTA))
    print(
        pensamento_personagem(
            nome,
            "Preciso abrir minha ficha depois. Esses pontos nao vao se gastar sozinhos.",
            CYAN,
        )
    )
    aguardar_enter("\nPressione Enter para respirar fundo...")
