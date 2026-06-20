import os


RESET = "\033[0m"
BOLD = "\033[1m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


def colorir(texto, cor):
    return f"{cor}{texto}{RESET}"


def caixa_texto(texto, largura=54, cor=CYAN):
    largura = max(largura, len(str(texto)) + 4)
    conteudo = str(texto).center(largura - 2)
    topo = "\u2554" + ("\u2550" * (largura - 2)) + "\u2557"
    meio = "\u2551" + conteudo + "\u2551"
    base = "\u255a" + ("\u2550" * (largura - 2)) + "\u255d"
    return "\n".join(colorir(linha, cor) for linha in (topo, meio, base))


def linha_pontilhada(largura=54, cor=MAGENTA):
    return colorir("\u00b7" * largura, cor)


def pensamento_personagem(nome, texto, cor=CYAN):
    return colorir(f"{nome}: '{texto}'", cor)


def fala_entidade(nome, texto, cor=MAGENTA):
    return colorir(f"{nome}: \"{texto}\"", cor)


def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")


def aguardar_enter(mensagem="\nPressione Enter para continuar...", limpar=True):
    input(mensagem)
    if limpar:
        limpar_tela()


def obter_entrada(mensagem, tipo=int, opcoes=None):
    while True:
        valor_bruto = input(mensagem).strip()

        try:
            valor = tipo(valor_bruto)
        except ValueError:
            nome_tipo = "numero" if tipo is int else tipo.__name__
            print(colorir(f"Opcao invalida! Digite um {nome_tipo}.", RED))
            continue

        if opcoes is not None and valor not in opcoes:
            print(colorir("Opcao invalida! Escolha uma opcao disponivel.", RED))
            continue

        return valor
