"""
Converte HTML em PDF.

Dois motores:

  "edge"       — usa o Microsoft Edge (ou Chrome) em modo headless. É o padrão
                 no Windows: já vem instalado no sistema, não precisa de DLL
                 nenhuma e sobrevive a ser empacotado num .exe.

  "weasyprint" — motor original do projeto. Melhor tipografia, mas no Windows
                 depende do GTK/Pango instalado à parte. Fica como alternativa
                 pra quem já tem o ambiente montado, e é o padrão no Linux/Mac.
"""

import os
import shutil
import subprocess
import sys
import tempfile

NAVEGADORES_WINDOWS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


class MotorIndisponivel(RuntimeError):
    """Levantado quando o motor pedido não tem como rodar nesta máquina."""


def encontrar_navegador():
    """Devolve o caminho do Edge/Chrome, ou None se não achar nenhum."""
    for caminho in NAVEGADORES_WINDOWS:
        if os.path.isfile(caminho):
            return caminho
    for nome in ("msedge", "chrome", "chromium", "google-chrome"):
        achado = shutil.which(nome)
        if achado:
            return achado
    return None


def _via_edge(html: str, caminho_saida: str, timeout: int = 120):
    navegador = encontrar_navegador()
    if not navegador:
        raise MotorIndisponivel(
            "Não encontrei o Microsoft Edge nem o Google Chrome nesta máquina."
        )

    saida = os.path.abspath(caminho_saida)

    # Apaga um PDF antigo que esteja no caminho: sem isso, uma falha do
    # navegador passaria despercebida — o arquivo velho continuaria lá e o
    # programa acharia que deu tudo certo.
    if os.path.exists(saida):
        os.remove(saida)

    # O navegador só imprime a partir de uma URL, então o HTML vai pro disco antes.
    temporaria = tempfile.mkdtemp(prefix="guia-pdf-")
    caminho_html = os.path.join(temporaria, "guia.html")
    perfil = os.path.join(temporaria, "perfil")
    try:
        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(html)

        processo = subprocess.Popen(
            [
                navegador,
                "--headless=new",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                # sem --user-data-dir próprio, o headless recusa a rodar quando
                # já existe uma janela normal do navegador aberta
                f"--user-data-dir={perfil}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={saida}",
                _para_url(caminho_html),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # O msedge.exe que chamamos costuma delegar para um processo filho e
        # sair com código 0 na hora, ANTES do PDF existir. Por isso quem manda
        # aqui é o arquivo aparecer, não o código de saída.
        erro = _esperar_arquivo(saida, timeout)

        processo.poll()
        if processo.returncode is None:
            processo.kill()  # não deixa navegador pendurado consumindo memória
            processo.wait(timeout=10)

        if erro:
            raise RuntimeError(
                f"O navegador não gerou o PDF em {timeout}s.\n"
                "Tente fechar as janelas abertas do Edge e gerar de novo."
            )
    finally:
        shutil.rmtree(temporaria, ignore_errors=True)


def _esperar_arquivo(caminho: str, timeout: int) -> bool:
    """
    Espera o arquivo aparecer E parar de crescer. Devolve True se desistiu.
    O navegador escreve o PDF aos poucos, então achar o arquivo não basta —
    é preciso ver o tamanho estabilizar antes de considerar pronto.
    """
    import time

    limite = time.monotonic() + timeout
    tamanho_anterior = -1
    estavel = 0

    while time.monotonic() < limite:
        if os.path.isfile(caminho):
            tamanho = os.path.getsize(caminho)
            if tamanho > 0 and tamanho == tamanho_anterior:
                estavel += 1
                if estavel >= 3:  # ~0,6s sem mudar de tamanho
                    return False
            else:
                estavel = 0
            tamanho_anterior = tamanho
        time.sleep(0.2)

    return True


def _via_weasyprint(html: str, caminho_saida: str):
    _preparar_gtk_windows()
    try:
        # import tardio: só carrega se for usar mesmo
        from weasyprint import HTML
    except ImportError as e:
        # o build_exe.py deixa o weasyprint de fora do pacote de propósito
        # (ele arrasta 138 MB de GTK), então no .exe esse caminho não existe
        raise MotorIndisponivel(
            "Esta versão do programa foi montada só com o motor do navegador — "
            "o weasyprint não veio junto.\n"
            "Use o motor \"edge\" (padrão) ou rode a partir do código-fonte."
        ) from e

    HTML(string=html, base_url=".").write_pdf(caminho_saida)


def _preparar_gtk_windows():
    """
    No Windows o weasyprint depende das DLLs do GTK/Pango, e desde o Python 3.8
    o PATH não é mais usado para resolver DLLs dependentes — daí o erro
    "cannot load library 'libgobject-2.0-0'". Aqui apontamos a pasta na mão.
    """
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return

    candidatos = []
    if os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        candidatos += os.environ["WEASYPRINT_DLL_DIRECTORIES"].split(os.pathsep)
    candidatos += [
        os.path.expanduser("~/GTK3-Runtime/bin"),
        "C:/Program Files/GTK3-Runtime Win64/bin",
        "C:/msys64/mingw64/bin",
    ]

    for pasta in candidatos:
        if os.path.isfile(os.path.join(pasta, "libgobject-2.0-0.dll")):
            os.add_dll_directory(os.path.abspath(pasta))
            return

    raise MotorIndisponivel(
        "O weasyprint precisa do GTK instalado no Windows e ele não está aqui.\n"
        "Use o motor \"edge\" (padrão) ou instale o GTK3 Runtime."
    )


def _para_url(caminho: str) -> str:
    from urllib.request import pathname2url

    return "file:" + pathname2url(os.path.abspath(caminho))


def motor_padrao() -> str:
    """Edge no Windows (não precisa instalar nada); weasyprint no resto."""
    if sys.platform == "win32" and encontrar_navegador():
        return "edge"
    return "weasyprint"


def html_para_pdf(html: str, caminho_saida: str, motor: str = "auto") -> str:
    if motor == "auto":
        motor = motor_padrao()

    pasta = os.path.dirname(os.path.abspath(caminho_saida))
    os.makedirs(pasta, exist_ok=True)

    if motor == "edge":
        _via_edge(html, caminho_saida)
    elif motor == "weasyprint":
        _via_weasyprint(html, caminho_saida)
    else:
        raise ValueError(f'motor desconhecido: {motor!r} (use "edge" ou "weasyprint")')

    return caminho_saida
