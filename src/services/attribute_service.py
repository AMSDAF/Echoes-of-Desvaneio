ATRIBUTOS_PADRAO = {
    "strength": 10,
    "dexterity": 10,
    "constitution": 10,
    "intelligence": 10,
    "wisdom": 10,
    "charisma": 10,
    "luck": 0,
}

NOMES_ATRIBUTOS = {
    "strength": "Forca",
    "dexterity": "Destreza",
    "constitution": "Constituicao",
    "intelligence": "Inteligencia",
    "wisdom": "Sabedoria",
    "charisma": "Carisma",
    "luck": "Sorte",
}

ATRIBUTOS_LEGADOS = {
    "agility": "dexterity",
    "vitality": "constitution",
}


def calcular_modificador_atributo(valor_atributo):
    return (int(valor_atributo) - 10) // 2


def normalizar_atributos(atributos):
    atributos = atributos or {}
    normalizados = dict(ATRIBUTOS_PADRAO)

    for attr, valor in atributos.items():
        attr_normalizado = ATRIBUTOS_LEGADOS.get(attr, attr)
        if attr_normalizado in normalizados:
            normalizados[attr_normalizado] = valor

    return normalizados


def formatar_percentual(chance):
    return f"{int(round(chance * 100))}%"
