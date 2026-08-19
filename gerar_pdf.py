"""
Pega os dados já estruturados (dict vindo do gerar_conteudo.py) e gera o PDF final,
aplicando a identidade visual definida em config.py.
"""

import os
import sys
from jinja2 import Environment, FileSystemLoader

import config
import motor_pdf


def _pasta_templates():
    """
    Empacotado com PyInstaller o programa roda de uma pasta temporaria
    (sys._MEIPASS), entao o caminho relativo 'templates' nao existe mais.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "templates")


def gerar_pdf(dados: dict, caminho_saida: str, motor: str = "auto"):
    env = Environment(loader=FileSystemLoader(_pasta_templates()))
    template = env.get_template("guia.html")

    html_renderizado = template.render(
        nome_igreja=config.NOME_IGREJA,
        cor_primaria=config.COR_PRIMARIA,
        cor_secundaria=config.COR_SECUNDARIA,
        cor_destaque=config.COR_DESTAQUE,
        lema=config.LEMA,
        instagram=config.INSTAGRAM,
        youtube=config.YOUTUBE,
        **dados,
    )

    return motor_pdf.html_para_pdf(html_renderizado, caminho_saida, motor=motor)


if __name__ == "__main__":
    # Dados de exemplo, só pra testar rapidamente sem rodar o pipeline inteiro
    dados_teste = {
        "tema": "Vigiai e Orai: Guardando Nosso Coração Enquanto Esperamos",
        "passagem_biblica": "Lucas 21:34-36",
        "pregador": "Pr. Exemplo",
        "data": "16 de agosto de 2026",
        "resumo_mensagem": (
            "Em Lucas 21:34-36, Jesus adverte seus discípulos para que cuidemos do "
            "coração, para que ele não fique sobrecarregado pela correria e pelas "
            "preocupações deste mundo. Nossa esperança não está na política, na "
            "economia ou na tecnologia; nossa esperança tem um nome, e esse nome é Jesus."
        ),
        "pontos_aplicacao": [
            {"titulo": "Proteja seu Lar da Correria",
             "texto": "É fácil deixar a agenda lotar até que o tempo com Deus desapareça. "
                       "Avalie a rotina da família e abra espaço para Ele."},
            {"titulo": "Mantenha os Sentidos Espirituais Alertas",
             "texto": "Escolha se encher da Palavra em vez de ansiedade e distração."},
            {"titulo": "Não Deixe as Preocupações Tomarem seu Lugar",
             "texto": "Coloque o trabalho e as contas no lugar certo, debaixo do senhorio de Deus."},
        ],
        "perguntas_discussao": [
            "O que tem ocupado seu coração ultimamente, deixando pouco espaço para Jesus?",
            "Onde a correria tem empurrado o tempo com Deus para fora da rotina?",
            "O que a família pode fazer essa semana para vigiar e orar de forma ativa?",
        ],
        "oracao_final": (
            "Senhor, viemos diante de Ti como família, gratos porque nada Te pega de "
            "surpresa. Guarda nosso coração da correria e das distrações. Em nome de Jesus, amém."
        ),
        "hino_sugerido": {
            "numero": "98",
            "titulo": "Estarás Vigiando?",
            "comentario": "Convida cada crente a examinar o coração e considerar se está pronto para a volta de Cristo.",
        },
    }

    caminho = gerar_pdf(dados_teste, "pdfs/exemplo.pdf")
    print(f"PDF gerado em: {caminho}")
