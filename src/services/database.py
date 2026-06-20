import json

def carregar_json(caminho_do_arquivo):
    try:
        with open(caminho_do_arquivo, 'r', encoding='utf-8') as f:
            # Se o arquivo estiver vazio, o json.load() falha, caindo no except
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Se o arquivo não existir ou estiver vazio/corrompido, retorna None de boa
        return None

def salvar_json(caminho_do_arquivo, dados):
    with open(caminho_do_arquivo, 'w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)