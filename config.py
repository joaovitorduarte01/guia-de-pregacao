"""
Configurações do sistema de Guia de Pregação.
Edite os valores abaixo com os dados da sua igreja.
"""

# --- Identidade da igreja ---
NOME_IGREJA = "Assembleia de Deus Lisboa"
LOGO_PATH = "static/logo.png"       # coloque o logo da igreja aqui (PNG, fundo transparente de preferência)
COR_PRIMARIA = "#0C2C5A"            # azul-marinho do cabeçalho e dos títulos
COR_SECUNDARIA = "#F1F4FA"          # fundo das caixas de destaque
COR_DESTAQUE = "#C8A23C"            # dourado dos detalhes (filetes, números dos pontos)
LEMA = "Evangelização: a chama não pode apagar"   # aparece no rodapé do PDF
INSTAGRAM = "@adlisboasj"           # instagram.com/adlisboasj
YOUTUBE = ""                        # deixe vazio para não aparecer no rodapé do PDF

# --- Transcrição (faster-whisper) ---
# Opções de modelo (da mais rápida/menos precisa para a mais lenta/mais precisa):
# "small" (~0,5 GB RAM), "medium" (~2,5 GB), "large-v3" (~5 GB)
# Este notebook tem 7,7 GB de RAM no total — "medium" junto com o modelo de IA
# estoura a memória e trava a máquina. Se um dia rodar num PC com 16 GB+,
# pode voltar para "medium" que a transcrição fica bem melhor.
WHISPER_MODEL = "small"
WHISPER_DEVICE = "cpu"      # troque para "cuda" se tiver placa de vídeo NVIDIA
WHISPER_COMPUTE_TYPE = "int8"  # "int8" é mais rápido em CPU; "float16" se usar GPU

# --- Geração de conteúdo (Ollama, rodando local e de graça) ---
OLLAMA_URL = "http://localhost:11434/api/chat"
# llama3.1 é de 8 bilhões de parâmetros e pede 5-6 GB de RAM só pra ele — não
# cabe nos 7,7 GB deste notebook (o Windows começa a usar o disco como memória
# e a máquina congela). llama3.2 é de 3B, ocupa ~2 GB e dá conta do português.
OLLAMA_MODEL = "llama3.2"   # rode antes: `ollama pull llama3.2`

# --- Pastas ---
PASTA_AUDIOS = "audios"
PASTA_PDFS = "pdfs"


# ---------------------------------------------------------------------------
# Ajustes salvos pelo aplicativo desktop
#
# Empacotado como .exe, este arquivo vira código congelado lá dentro — ninguém
# consegue abrir e editar o nome da igreja. Então os valores acima passam a ser
# apenas os PADRÕES, e o que a pessoa preencher na tela de Configurações fica
# guardado num JSON à parte, que é lido aqui e sobrescreve os padrões.
# ---------------------------------------------------------------------------

import json as _json
import os as _os

AJUSTAVEIS = (
    "NOME_IGREJA", "LEMA", "LOGO_PATH", "COR_PRIMARIA", "COR_SECUNDARIA", "COR_DESTAQUE",
    "INSTAGRAM", "YOUTUBE", "WHISPER_MODEL", "OLLAMA_MODEL", "OLLAMA_URL",
)


def caminho_ajustes() -> str:
    """Um JSON na pasta do usuário — funciona tanto rodando o .py quanto o .exe."""
    base = _os.environ.get("APPDATA") or _os.path.expanduser("~")
    return _os.path.join(base, "GuiaPregacao", "configuracao.json")


def carregar_ajustes():
    """Sobrescreve os padrões acima com o que estiver salvo no JSON."""
    try:
        with open(caminho_ajustes(), encoding="utf-8") as f:
            salvos = _json.load(f)
    except (OSError, ValueError):
        return {}

    aplicados = {}
    for chave, valor in salvos.items():
        if chave in AJUSTAVEIS and isinstance(valor, str) and valor.strip():
            globals()[chave] = valor
            aplicados[chave] = valor
    return aplicados


def salvar_ajustes(novos: dict):
    """Grava o JSON e já aplica na sessão atual."""
    caminho = caminho_ajustes()
    _os.makedirs(_os.path.dirname(caminho), exist_ok=True)

    atuais = {}
    try:
        with open(caminho, encoding="utf-8") as f:
            atuais = _json.load(f)
    except (OSError, ValueError):
        pass

    for chave, valor in novos.items():
        if chave in AJUSTAVEIS:
            atuais[chave] = valor
            globals()[chave] = valor

    with open(caminho, "w", encoding="utf-8") as f:
        _json.dump(atuais, f, indent=2, ensure_ascii=False)
    return caminho


carregar_ajustes()
