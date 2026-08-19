"""
Gera o PDF com o passo a passo de instalação em outro computador.

    python gerar_manual.py

Sai em pdfs/Como-instalar-o-Guia-de-Pregacao.pdf, pronto pra imprimir ou mandar
junto com o link de download.

Usa o mesmo motor e a mesma identidade visual do guia da pregação, então quando
a igreja trocar de cor no config o manual acompanha.
"""

import os
import sys

from jinja2 import Environment, FileSystemLoader

import config
import motor_pdf

URL_DOWNLOAD = "https://github.com/joaovitorduarte01/guia-de-pregacao/releases/latest"
NOME_ARQUIVO = "GuiaDePregacao-Windows.zip"
TAMANHO_MB = 98

SAIDA = os.path.join("pdfs", "Como-instalar-o-Guia-de-Pregacao.pdf")


def _pasta_templates():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "templates")


def gerar(caminho_saida=SAIDA, motor="auto"):
    env = Environment(loader=FileSystemLoader(_pasta_templates()))
    template = env.get_template("manual.html")

    html = template.render(
        nome_igreja=config.NOME_IGREJA,
        lema=config.LEMA,
        instagram=config.INSTAGRAM,
        cor_primaria=config.COR_PRIMARIA,
        cor_secundaria=config.COR_SECUNDARIA,
        cor_destaque=config.COR_DESTAQUE,
        url_download=URL_DOWNLOAD,
        nome_arquivo=NOME_ARQUIVO,
        tamanho_mb=TAMANHO_MB,
    )

    return motor_pdf.html_para_pdf(html, caminho_saida, motor=motor)


if __name__ == "__main__":
    caminho = gerar()
    print(f"manual gerado em: {os.path.abspath(caminho)}")
