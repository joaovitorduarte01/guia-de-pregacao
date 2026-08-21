"""
Preparação automática da máquina na primeira execução.

Descobre o que está faltando (Ollama, modelo de IA, modelo de transcrição),
escolhe modelos que caibam na memória do computador e baixa tudo mostrando
progresso — sem a pessoa precisar abrir Prompt de Comando nenhum.

O que este módulo NÃO faz de propósito: instalar nada sem a pessoa mandar. São
uns 3 GB de download e software de terceiro entrando na máquina; isso se
pergunta antes. A função `preparar()` só roda depois de um clique consciente.
"""

import json
import os
import shutil
import subprocess
import sys
import time

import requests

import config

URL_INSTALADOR_OLLAMA = "https://ollama.com/download/OllamaSetup.exe"

# Quanto cada modelo ocupa de memória enquanto roda, aproximadamente.
CUSTO_OLLAMA = {"llama3.2": 2.0, "llama3.1": 5.5, "mistral": 4.5}
CUSTO_WHISPER = {"small": 0.6, "medium": 2.5, "large-v3": 5.0}

ESPACO_MINIMO_GB = 6


class Cancelado(Exception):
    """A pessoa fechou a janela ou clicou em cancelar no meio do processo."""


# --------------------------------------------------------------- diagnóstico

def caminho_ollama():
    """Onde está o ollama.exe, ou None se não estiver instalado."""
    candidatos = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Ollama\ollama.exe"),
    ]
    for c in candidatos:
        if os.path.isfile(c):
            return c
    achado = shutil.which("ollama")
    return achado


def _url_base():
    return config.OLLAMA_URL.replace("/api/chat", "")


def servidor_no_ar(timeout=2) -> bool:
    try:
        requests.get(f"{_url_base()}/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def modelos_instalados():
    try:
        r = requests.get(f"{_url_base()}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def modelo_presente(nome: str) -> bool:
    curto = nome.split(":")[0]
    return any(m.split(":")[0] == curto for m in modelos_instalados())


def whisper_em_cache(nome: str) -> bool:
    """O faster-whisper guarda os modelos no cache do huggingface."""
    base = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    pasta = os.path.join(base, f"models--Systran--faster-whisper-{nome}")
    if not os.path.isdir(pasta):
        return False
    # existir a pasta não basta: um download interrompido deixa ela pela metade
    for raiz, _, arquivos in os.walk(pasta):
        for a in arquivos:
            if a == "model.bin" and os.path.getsize(os.path.join(raiz, a)) > 1_000_000:
                return True
    return False


def memoria_total_gb() -> float:
    """RAM da máquina em GB. Sem depender de biblioteca externa."""
    if sys.platform == "win32":
        import ctypes

        class Status(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        s = Status()
        s.dwLength = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return s.ullTotalPhys / (1024 ** 3)

    try:
        return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024 ** 3)
    except (ValueError, AttributeError):
        return 8.0


def espaco_livre_gb(caminho=None) -> float:
    return shutil.disk_usage(caminho or os.path.expanduser("~")).free / (1024 ** 3)


def recomendar_modelos() -> dict:
    """
    Escolhe modelos que caibam na máquina. Os dois rodam ao mesmo tempo, então
    o que importa é a soma — pedir mais do que existe não dá erro, faz o
    Windows paginar em disco e travar o computador.
    """
    ram = memoria_total_gb()
    if ram >= 30:
        return {"ollama": "llama3.1", "whisper": "large-v3", "ram": ram}
    if ram >= 15:
        return {"ollama": "llama3.1", "whisper": "medium", "ram": ram}
    return {"ollama": "llama3.2", "whisper": "small", "ram": ram}


def diagnostico() -> dict:
    """Fotografia do que está pronto e do que falta."""
    ollama = caminho_ollama()
    no_ar = servidor_no_ar()
    return {
        "ollama_instalado": bool(ollama),
        "caminho_ollama": ollama,
        "servidor_no_ar": no_ar,
        "modelo_ia": modelo_presente(config.OLLAMA_MODEL) if no_ar else False,
        "modelo_transcricao": whisper_em_cache(config.WHISPER_MODEL),
        "ram_gb": memoria_total_gb(),
        "espaco_livre_gb": espaco_livre_gb(),
    }


def tudo_pronto(d=None) -> bool:
    d = d or diagnostico()
    return d["servidor_no_ar"] and d["modelo_ia"] and d["modelo_transcricao"]


def falta_baixar_gb(d=None) -> float:
    """Estimativa do download, pra avisar antes de começar."""
    d = d or diagnostico()
    total = 0.0
    if not d["ollama_instalado"]:
        total += 1.1
    if not d["modelo_ia"]:
        total += CUSTO_OLLAMA.get(config.OLLAMA_MODEL.split(":")[0], 2.5)
    if not d["modelo_transcricao"]:
        total += CUSTO_WHISPER.get(config.WHISPER_MODEL, 0.6)
    return total


# ------------------------------------------------------------------ execução

def _baixar(url: str, destino: str, aviso, cancelou):
    resposta = requests.get(url, stream=True, timeout=60)
    resposta.raise_for_status()
    total = int(resposta.headers.get("Content-Length") or 0)
    baixado = 0

    with open(destino, "wb") as f:
        for pedaco in resposta.iter_content(chunk_size=1024 * 256):
            if cancelou():
                raise Cancelado()
            f.write(pedaco)
            baixado += len(pedaco)
            if total:
                aviso(baixado / total,
                      f"{baixado / 1048576:.0f} MB de {total / 1048576:.0f} MB")
            else:
                aviso(None, f"{baixado / 1048576:.0f} MB")
    return destino


def instalar_ollama(aviso, cancelou):
    import tempfile

    pasta = tempfile.mkdtemp(prefix="setup-ollama-")
    instalador = os.path.join(pasta, "OllamaSetup.exe")
    try:
        aviso(0.0, "conectando...")
        _baixar(URL_INSTALADOR_OLLAMA, instalador, aviso, cancelou)

        aviso(None, "instalando (pode levar um minuto)...")
        # O instalador do Ollama é Inno Setup e aceita instalação silenciosa.
        subprocess.run(
            [instalador, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            check=False, capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # dá um tempo pro instalador terminar de escrever os arquivos
        for _ in range(30):
            if caminho_ollama():
                return True
            time.sleep(1)

        # Silencioso não pegou — abre o instalador normal pra pessoa clicar.
        # Melhor isso do que falhar sem explicação.
        aviso(None, "abrindo o instalador — siga os passos na tela")
        subprocess.run([instalador], check=False)
        for _ in range(120):
            if cancelou():
                raise Cancelado()
            if caminho_ollama():
                return True
            time.sleep(1)
        return False
    finally:
        # o .exe pode ainda estar em uso; se não der pra apagar, tudo bem
        shutil.rmtree(pasta, ignore_errors=True)


def iniciar_servidor(aviso) -> bool:
    if servidor_no_ar():
        return True

    exe = caminho_ollama()
    if not exe:
        return False

    aviso(None, "ligando o motor de IA...")
    # o serviço fica de pé sozinho depois disso; sem janela preta na tela
    #
    # cwd é obrigatório aqui: processo filho herda o diretório atual do pai, e
    # o do aplicativo é a própria pasta de instalação. O Windows não deixa
    # renomear nem apagar uma pasta que é o diretório atual de algum processo,
    # então o Ollama de pé trancava a pasta do programa — quem quisesse mover
    # ou desinstalar o aplicativo esbarrava num "arquivo em uso" sem entender
    # de onde vinha.
    subprocess.Popen(
        [exe, "serve"],
        cwd=os.path.expanduser("~"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for _ in range(30):
        if servidor_no_ar():
            return True
        time.sleep(1)
    return False


def puxar_modelo(nome: str, aviso, cancelou):
    """
    Baixa o modelo pela API do Ollama, que devolve o progresso em streaming —
    bem melhor que ler a saída do comando de terminal.
    """
    resposta = requests.post(
        f"{_url_base()}/api/pull",
        json={"model": nome, "stream": True},
        stream=True, timeout=(10, 600),
    )
    resposta.raise_for_status()

    for linha in resposta.iter_lines():
        if cancelou():
            raise Cancelado()
        if not linha:
            continue
        try:
            evento = json.loads(linha)
        except ValueError:
            continue

        if evento.get("error"):
            raise RuntimeError(evento["error"])

        total = evento.get("total") or 0
        feito = evento.get("completed") or 0
        estado = evento.get("status", "")
        if total:
            aviso(feito / total,
                  f"{feito / 1048576:.0f} MB de {total / 1048576:.0f} MB")
        else:
            aviso(None, estado)

    if not modelo_presente(nome):
        raise RuntimeError(f'O modelo "{nome}" não apareceu depois do download.')


def baixar_modelo_transcricao(nome: str, aviso):
    """
    Não tem como acompanhar o progresso aqui: quem baixa é o faster-whisper por
    baixo. Carregar o modelo uma vez força o download e deixa em cache.
    """
    aviso(None, "baixando o modelo de transcrição (alguns minutos)...")
    from faster_whisper import WhisperModel

    WhisperModel(nome, device=config.WHISPER_DEVICE,
                 compute_type=config.WHISPER_COMPUTE_TYPE)


def preparar(passo, aviso, cancelou=lambda: False):
    """
    Deixa a máquina pronta. Chama `passo(numero, total, titulo)` a cada etapa e
    `aviso(fracao_ou_None, detalhe)` durante cada uma.

    Só chame depois de a pessoa aceitar — baixa alguns GB.
    """
    d = diagnostico()

    if d["espaco_livre_gb"] < ESPACO_MINIMO_GB:
        raise RuntimeError(
            f"Espaço em disco insuficiente: {d['espaco_livre_gb']:.1f} GB livres, "
            f"e são necessários pelo menos {ESPACO_MINIMO_GB} GB."
        )

    etapas = []
    if not d["ollama_instalado"]:
        etapas.append("ollama")
    if not d["servidor_no_ar"] or not d["ollama_instalado"]:
        etapas.append("servidor")
    if not d["modelo_ia"]:
        etapas.append("modelo_ia")
    if not d["modelo_transcricao"]:
        etapas.append("whisper")

    total = len(etapas)
    for i, etapa in enumerate(etapas, start=1):
        if cancelou():
            raise Cancelado()

        if etapa == "ollama":
            passo(i, total, "Instalando o motor de IA (Ollama)")
            if not instalar_ollama(aviso, cancelou):
                raise RuntimeError(
                    "Não consegui instalar o Ollama automaticamente.\n"
                    "Instale à mão em ollama.com/download e abra o programa de novo."
                )

        elif etapa == "servidor":
            passo(i, total, "Ligando o motor de IA")
            if not iniciar_servidor(aviso):
                raise RuntimeError("O Ollama foi instalado mas não quis iniciar.")

        elif etapa == "modelo_ia":
            passo(i, total, f"Baixando o modelo {config.OLLAMA_MODEL}")
            puxar_modelo(config.OLLAMA_MODEL, aviso, cancelou)

        elif etapa == "whisper":
            passo(i, total, f"Baixando a transcrição ({config.WHISPER_MODEL})")
            baixar_modelo_transcricao(config.WHISPER_MODEL, aviso)


if __name__ == "__main__":
    d = diagnostico()
    print("--- diagnóstico ---")
    for chave, valor in d.items():
        print(f"  {chave:22} {valor}")
    print(f"\n  recomendado pra esta máquina: {recomendar_modelos()}")
    print(f"  falta baixar: ~{falta_baixar_gb(d):.1f} GB")
    print(f"  tudo pronto: {tudo_pronto(d)}")
