"""
Gera o executável do aplicativo desktop.

    pip install pyinstaller
    python build_exe.py

O resultado sai em  dist/Guia de Pregacao/  — é essa PASTA inteira que se
distribui (zipada, ou com um instalador). Dentro dela tem o
"Guia de Pregacao.exe", que a pessoa abre com duplo clique.

Por que pasta e não arquivo único: no modo --onefile o Windows descompacta
tudo num diretório temporário a cada abertura. Como o faster-whisper carrega
mais de 100 MB de bibliotecas, isso deixa a abertura lenta toda vez. Em pasta,
abre na hora.

O que NÃO vai junto (e nem tem como ir):
  - o Ollama, que é um programa separado de ~1 GB — o app avisa se faltar
  - o modelo do Whisper, que é baixado sozinho na primeira transcrição
"""

import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
NOME = "Guia de Pregacao"

# Módulos que o PyInstaller não enxerga sozinho porque só são importados
# indiretamente, dentro das bibliotecas.
IMPORTS_OCULTOS = [
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "tokenizers",
    "huggingface_hub",
    # estes são importados dentro de funções (pra janela abrir rápido), então
    # ficam listados aqui pra garantir que entrem no pacote
    "instalador",
    "tela_preparo",
    "tela_revisao",
    "tema",
    "transcrever",
    "gerar_conteudo",
    "harpa",
    "gerar_pdf",
    "motor_pdf",
]

# Peso morto: entra no pacote sem ninguém usar. Streamlit e companhia só
# existem por causa da interface antiga (app.py), e o weasyprint só roda com
# GTK instalado à parte — o motor padrão aqui é o Edge.
EXCLUIR = [
    "streamlit", "altair", "pandas", "pyarrow", "pydeck", "watchdog",
    "weasyprint", "pydyf", "cssselect2", "tinycss2", "tinyhtml5", "Pyphen",
    "matplotlib", "scipy", "IPython", "pytest", "PIL.ImageQt",
    "PySide6", "PyQt5", "PyQt6",
]


def app_aberto() -> bool:
    """
    O .exe está em uso? No Windows um arquivo em execução não pode ser
    renomeado — é o teste mais direto, e não depende de biblioteca nenhuma.
    """
    exe = os.path.join(AQUI, "dist", NOME, f"{NOME}.exe")
    if not os.path.isfile(exe):
        return False
    try:
        os.rename(exe, exe + ".emuso")
        os.rename(exe + ".emuso", exe)
        return False
    except OSError:
        return True


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("O PyInstaller não está instalado. Rode antes:\n\n    "
              f"{sys.executable} -m pip install pyinstaller\n")
        return 1

    # Já aconteceu de reconstruir com o aplicativo aberto: o rmtree apaga o que
    # consegue, esbarra nos arquivos travados, e com ignore_errors nem reclama.
    # O programa fica aberto na tela da pessoa apontando pra uma pasta que não
    # existe mais. Melhor parar aqui.
    if app_aberto():
        print(f'O "{NOME}" está aberto. Feche a janela dele antes de '
              "reconstruir,\nsenão a instalação atual é destruída pela metade.")
        return 1

    for pasta in ("build", "dist"):
        caminho = os.path.join(AQUI, pasta)
        if os.path.isdir(caminho):
            print(f"limpando {pasta}/ ...")
            try:
                shutil.rmtree(caminho)
            except OSError as erro:
                # sem ignore_errors: apagar pela metade é pior que não apagar
                print(f"não deu pra limpar {pasta}/: {erro}")
                return 1

    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",                 # sem janela preta de terminal atrás
        "--name", NOME,
        # o template do PDF precisa viajar junto; gerar_pdf.py acha ele pelo
        # sys._MEIPASS quando está empacotado
        "--add-data", f"{os.path.join(AQUI, 'templates')}{os.pathsep}templates",
        "--collect-data", "faster_whisper",
    ]

    icone = os.path.join(AQUI, "static", "icone.ico")
    if os.path.isfile(icone):
        comando += ["--icon", icone]
    else:
        print("(sem static/icone.ico — o .exe vai sair com o ícone padrão)")

    for modulo in IMPORTS_OCULTOS:
        comando += ["--hidden-import", modulo]
    for modulo in EXCLUIR:
        comando += ["--exclude-module", modulo]

    comando.append(os.path.join(AQUI, "app_desktop.py"))

    print("\nempacotando (leva alguns minutos e usa bastante CPU)...\n")
    resultado = subprocess.run(comando, cwd=AQUI)
    if resultado.returncode != 0:
        return resultado.returncode

    destino = os.path.join(AQUI, "dist", NOME)
    tamanho = sum(
        os.path.getsize(os.path.join(raiz, f))
        for raiz, _, arquivos in os.walk(destino)
        for f in arquivos
    )
    print(f"\npronto: {destino}")
    print(f"tamanho: {tamanho / 1024 / 1024:.0f} MB")
    print(f"execute: {os.path.join(destino, NOME + '.exe')}")
    print()
    print("para pôr o atalho na Área de Trabalho:  python criar_atalho.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
