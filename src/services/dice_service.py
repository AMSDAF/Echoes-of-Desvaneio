import random

from src.services.attribute_service import NOMES_ATRIBUTOS


def rolar_d20_interativo(motivo="Teste", atributo=None, dc=None):
    partes = [motivo]
    if atributo:
        partes.append(NOMES_ATRIBUTOS.get(atributo, atributo))
    if dc is not None:
        partes.append(f"CD {dc}")

    contexto = " | ".join(partes)
    input(f"\n[ROLAGEM D20] {contexto}. Pressione Enter para rolar o dado...")
    resultado = random.randint(1, 20)
    print(f"O dado rola pela mesa... d20 = {resultado}")
    return resultado
