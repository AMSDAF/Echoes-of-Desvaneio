from functools import lru_cache
from pathlib import Path

from src.services.database import carregar_json


CITIES_ROOT = Path("data/cities")


def _normalizar_city_id(city_id):
    nome = str(city_id or "phandalin").strip().lower()
    if ". " in nome:
        nome = nome.split(". ", 1)[1]
    return nome.strip()


def _city_id_from_folder(folder):
    return _normalizar_city_id(folder.name)


@lru_cache(maxsize=None)
def localizar_pasta_cidade(city_id):
    city_id = _normalizar_city_id(city_id)
    if not CITIES_ROOT.exists():
        return None

    for folder in CITIES_ROOT.iterdir():
        if folder.is_dir() and _city_id_from_folder(folder) == city_id:
            return folder

    return None


@lru_cache(maxsize=None)
def carregar_dados_cidade(city_id, filename):
    folder = localizar_pasta_cidade(city_id)
    if folder is None:
        return {}

    arquivo = folder / Path(filename).name
    if not arquivo.is_file():
        return {}

    dados = carregar_json(str(arquivo))
    return dados if isinstance(dados, dict) else {}


def carregar_exploracao_cidade(city_id):
    return carregar_dados_cidade(city_id, "exploration.json")


def carregar_inimigos_cidade(city_id):
    return carregar_dados_cidade(city_id, "enemies.json")


def carregar_bestiario_cidade(city_id):
    return carregar_dados_cidade(city_id, "bestiary.json")


def carregar_npcs_cidade(city_id):
    return carregar_dados_cidade(city_id, "npcs.json")


def carregar_quests_cidade(city_id):
    return carregar_dados_cidade(city_id, "quests.json")


def carregar_taverna_cidade(city_id):
    return carregar_dados_cidade(city_id, "tavern.json")


def carregar_eventos_cidade(city_id):
    return carregar_dados_cidade(city_id, "town_events.json")


def carregar_lojas_cidade(city_id):
    return carregar_dados_cidade(city_id, "shops.json")
