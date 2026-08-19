"""
Envia a transcrição crua para um modelo de IA rodando LOCALMENTE via Ollama
(gratuito, sem limite de uso, sem mandar dados pra fora do seu computador)
e recebe de volta o conteúdo já organizado no formato do guia.

Uma pregação inteira NÃO cabe de uma vez na janela de contexto do modelo. O
Ollama trabalha com 4096 tokens por padrão, e 50 minutos de fala dão umas
9.800 — o que passa disso ele descarta sem avisar. O guia sairia completo e
bem formatado, mas baseado só num pedaço do que foi pregado.

Por isso, quando a transcrição é longa, ela é lida em partes: cada trecho vira
um resumo, e o guia final é montado a partir dos resumos juntos. Assim a
pregação inteira é considerada, e de quebra fica mais rápido — contexto menor
pesa menos na memória.
"""

import json
import re

import requests

import config

# O que o Ollama usa por padrão. Dá para aumentar, mas cada token a mais custa
# memória, e em máquina apertada isso derruba a velocidade mais do que ajuda.
CONTEXTO = 4096
RESERVA_RESPOSTA = 1000   # espaço que a resposta do modelo vai ocupar
RESERVA_INSTRUCOES = 800  # espaço do PROMPT_SISTEMA

# Sobra para o texto da pregação em cada chamada
ESPACO_TEXTO = CONTEXTO - RESERVA_RESPOSTA - RESERVA_INSTRUCOES

# Português rende ~3,5 caracteres por token. Estimativa grosseira de propósito:
# errar para menos é seguro, errar para mais faria o modelo cortar conteúdo.
CARACTERES_POR_TOKEN = 3.5

PROMPT_SISTEMA = """\
Você é um assistente que transforma a transcrição de uma pregação em um \
GUIA DE ESTUDO EM FAMÍLIA, em português do Brasil, seguindo EXATAMENTE esta \
estrutura em JSON (responda SOMENTE o JSON, sem markdown, sem texto antes ou depois):

{
  "tema": "título curto e impactante da pregação",
  "passagem_biblica": "ex: Lucas 21:34-36",
  "resumo_mensagem": "um parágrafo (6 a 10 frases) resumindo a mensagem central da pregação",
  "pontos_aplicacao": [
    {"titulo": "título curto do ponto", "texto": "parágrafo explicando o ponto e como aplicar na vida/família"},
    {"titulo": "...", "texto": "..."},
    {"titulo": "...", "texto": "..."}
  ],
  "perguntas_discussao": [
    "pergunta 1 para reflexão em família",
    "pergunta 2",
    "pergunta 3"
  ],
  "oracao_final": "um parágrafo de oração relacionado ao tema, em primeira pessoa do plural (nós)",
  "hino_sugerido": {
    "numero": "número do hino da Harpa Cristã, se conseguir identificar um que combine; senão deixe null",
    "titulo": "título do hino",
    "comentario": "uma ou duas frases relacionando o hino ao tema"
  }
}

Regras importantes:
- Use APENAS o conteúdo da transcrição como base. Não invente doutrina nem versículos que não foram citados.
- Se a transcrição não deixar claro algum campo (ex: passagem bíblica exata), faça sua melhor inferência a partir do contexto.
- Sempre gere exatamente 3 pontos de aplicação e 3 perguntas de discussão.
- Escreva em tom pastoral, caloroso e aplicável à vida real da família.
"""

PROMPT_RESUMO = """\
Você recebe um TRECHO da transcrição de uma pregação — não é a pregação inteira.

Resuma fielmente o que foi dito neste trecho, em português do Brasil, em até 8
frases. Registre:
- os pontos ensinados e os exemplos usados;
- toda passagem bíblica citada, com o nome do livro e o capítulo;
- as aplicações práticas sugeridas ao ouvinte.

Não conclua nem interprete além do que está escrito, e não invente versículo
que não apareça no trecho. Responda apenas com o resumo, em texto corrido.
"""


def _tokens_aprox(texto: str) -> int:
    return int(len(texto) / CARACTERES_POR_TOKEN)


def _conversar(mensagens, formato_json=False, timeout=1800) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": mensagens,
        "stream": False,
        "options": {"num_ctx": CONTEXTO},
    }
    if formato_json:
        payload["format"] = "json"

    resposta = requests.post(config.OLLAMA_URL, json=payload, timeout=timeout)
    resposta.raise_for_status()
    return resposta.json()["message"]["content"]


def _extrair_json(texto: str) -> dict:
    """Remove cercas de markdown (```json ... ```) se existirem e faz o parse."""
    texto = texto.strip()
    texto = re.sub(r"^```(json)?", "", texto).strip()
    texto = re.sub(r"```$", "", texto).strip()
    return json.loads(texto)


def fatiar(transcricao: str, tokens_por_fatia: int = None) -> list:
    """
    Divide a transcrição em pedaços que caibam no contexto.

    Corta em fim de frase sempre que possível — cortar no meio de uma ideia faz
    o resumo do trecho sair truncado e o guia herda o erro.
    """
    tokens_por_fatia = tokens_por_fatia or ESPACO_TEXTO
    limite = int(tokens_por_fatia * CARACTERES_POR_TOKEN)

    if len(transcricao) <= limite:
        return [transcricao]

    # separa mantendo a pontuação junto da frase
    frases = re.split(r"(?<=[.!?])\s+", transcricao)

    fatias, atual = [], ""
    for frase in frases:
        # frase gigante (Whisper às vezes devolve tudo sem pontuação): parte na marra
        while len(frase) > limite:
            if atual:
                fatias.append(atual.strip())
                atual = ""
            fatias.append(frase[:limite])
            frase = frase[limite:]

        if len(atual) + len(frase) + 1 > limite:
            fatias.append(atual.strip())
            atual = frase
        else:
            atual = f"{atual} {frase}".strip()

    if atual.strip():
        fatias.append(atual.strip())
    return [f for f in fatias if f]


def gerar_guia(transcricao: str, pregador: str, data: str, progresso=None) -> dict:
    """
    Chama o Ollama local e devolve um dicionário já estruturado, pronto para o
    template do PDF.

    `progresso` é chamado como progresso(fracao, descricao) durante o caminho,
    porque em máquina sem placa de vídeo isso leva muitos minutos e a pessoa
    precisa ver que algo está acontecendo.
    """
    def avisar(fracao, texto):
        if progresso:
            progresso(fracao, texto)

    transcricao = transcricao.strip()
    fatias = fatiar(transcricao)

    if len(fatias) == 1:
        avisar(0.1, "Organizando o conteúdo com a IA...")
        material = transcricao
    else:
        # Lê a pregação por partes e resume cada uma. Sem isto, tudo o que
        # passasse de ~4000 tokens seria descartado pelo Ollama sem aviso.
        resumos = []
        for i, fatia in enumerate(fatias, start=1):
            avisar(i / (len(fatias) + 1),
                   f"Lendo a pregação — parte {i} de {len(fatias)}...")
            resumos.append(_conversar([
                {"role": "system", "content": PROMPT_RESUMO},
                {"role": "user", "content": fatia},
            ]).strip())

        material = "\n\n".join(
            f"[Parte {i} da pregação]\n{r}" for i, r in enumerate(resumos, start=1)
        )
        avisar(len(fatias) / (len(fatias) + 1), "Montando o guia...")

    conteudo = _conversar(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Transcrição da pregação:\n\n{material}"},
        ],
        formato_json=True,
    )

    dados = _extrair_json(conteudo)
    dados["pregador"] = pregador
    dados["data"] = data
    return dados


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        texto = open(sys.argv[1], encoding="utf-8").read()
    else:
        texto = ("Hoje vamos falar sobre vigiar e orar. "
                 "[passe um arquivo .txt como argumento para testar de verdade]")

    fatias = fatiar(texto)
    print(f"transcrição: {len(texto)} caracteres (~{_tokens_aprox(texto)} tokens)")
    print(f"será lida em {len(fatias)} parte(s)\n")

    resultado = gerar_guia(
        texto, pregador="Pr. Exemplo", data="19 de agosto de 2026",
        progresso=lambda f, t: print(f"  [{f * 100:3.0f}%] {t}"),
    )
    print()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
