"""
Cria o atalho do programa na Área de Trabalho e no Menu Iniciar.

    python criar_atalho.py

Funciona tanto apontando pro executável (depois do build_exe.py) quanto pro
código-fonte, aí ele monta um atalho que chama o Python direto.

Usa o WScript.Shell via PowerShell em vez da biblioteca pywin32 — é o mesmo
resultado sem acrescentar dependência ao projeto só pra criar um .lnk.
"""

import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
NOME_ATALHO = "Guia de Pregação"


def caminho_executavel():
    """O .exe empacotado, se existir."""
    exe = os.path.join(AQUI, "dist", "Guia de Pregacao", "Guia de Pregacao.exe")
    return exe if os.path.isfile(exe) else None


def _powershell(script: str) -> str:
    """
    O PowerShell escreve na codepage do sistema, não em UTF-8. Sem forçar a
    saída, um caminho como "C:\\Users\\...\\OneDrive\\Área de Trabalho" volta
    com o acento quebrado e o os.path.isdir não encontra a pasta.
    """
    preambulo = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         preambulo + script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if resultado.returncode != 0:
        raise RuntimeError((resultado.stderr or "").strip() or "falha no PowerShell")
    return (resultado.stdout or "").strip()


def pastas_de_destino():
    """
    Área de Trabalho e Menu Iniciar. A Área de Trabalho vem pelo
    GetFolderPath e não por %USERPROFILE%\\Desktop de propósito: em máquina
    com OneDrive ela fica redirecionada e o caminho montado na mão erra.
    """
    saida = _powershell(
        "[Environment]::GetFolderPath('Desktop'); "
        "[Environment]::GetFolderPath('Programs')"
    )
    linhas = [linha.strip() for linha in saida.splitlines() if linha.strip()]
    return linhas[0], (linhas[1] if len(linhas) > 1 else None)


def criar(destino_lnk, alvo, argumentos="", pasta_trabalho="", icone=""):
    def escapar(texto):
        return str(texto).replace("'", "''")

    script = f"""
$s = New-Object -ComObject WScript.Shell
$a = $s.CreateShortcut('{escapar(destino_lnk)}')
$a.TargetPath = '{escapar(alvo)}'
$a.Arguments = '{escapar(argumentos)}'
$a.WorkingDirectory = '{escapar(pasta_trabalho)}'
$a.Description = 'Transforma o áudio da pregação em um guia de estudo em PDF'
"""
    if icone:
        script += f"$a.IconLocation = '{escapar(icone)}'\n"
    script += "$a.Save()\n"

    _powershell(script)
    return destino_lnk


def main():
    exe = caminho_executavel()

    if exe:
        alvo, argumentos = exe, ""
        pasta_trabalho = os.path.dirname(exe)
        icone = exe  # o ícone já está embutido no executável
        print(f"apontando para o executável:\n  {exe}\n")
    else:
        # sem build ainda: atalho que chama o Python direto no código-fonte.
        # pythonw.exe e não python.exe — o outro abre uma janela preta junto.
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        alvo = pythonw if os.path.isfile(pythonw) else sys.executable
        argumentos = f'"{os.path.join(AQUI, "app_desktop.py")}"'
        pasta_trabalho = AQUI
        icone = os.path.join(AQUI, "static", "icone.ico")
        if not os.path.isfile(icone):
            icone = ""
        print("não achei o executável (rode build_exe.py para gerá-lo).\n"
              f"criando atalho para o código-fonte via {os.path.basename(alvo)}\n")

    area_trabalho, menu_iniciar = pastas_de_destino()

    criados = []
    for pasta in (area_trabalho, menu_iniciar):
        if not pasta or not os.path.isdir(pasta):
            continue
        caminho = os.path.join(pasta, f"{NOME_ATALHO}.lnk")
        criar(caminho, alvo, argumentos, pasta_trabalho, icone)
        criados.append(caminho)

    for caminho in criados:
        print(f"criado: {caminho}")
    if not criados:
        print("não consegui criar o atalho em nenhuma pasta.")
    return 0 if criados else 1


if __name__ == "__main__":
    sys.exit(main())
