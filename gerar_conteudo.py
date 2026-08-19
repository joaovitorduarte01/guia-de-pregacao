"""
Envia a transcrição crua para um modelo de IA rodando LOCALMENTE via Ollama
(gratuito, sem limite de uso, sem mandar dados pra fora do seu computador)
e recebe de volta o conteúdo já organizado no formato do guia.
"""

import json
import re
import requests
import config

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


def _extrair_json(texto: str) -> dict:
    """Remove cercas de markdown (```json ... ```) se existirem e faz o parse."""
    texto = texto.strip()
    texto = re.sub(r"^```(json)?", "", texto).strip()
    texto = re.sub(r"```$", "", texto).strip()
    return json.loads(texto)


def gerar_guia(transcricao: str, pregador: str, data: str) -> dict:
    """
    Chama o Ollama local e devolve um dicionário já estruturado
    pronto para ser usado no template do PDF.
    """
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Transcrição da pregação:\n\n{transcricao}"},
        ],
        "stream": False,
        "format": "json",
    }

    resposta = requests.post(config.OLLAMA_URL, json=payload, timeout=600)
    resposta.raise_for_status()
    conteudo = resposta.json()["message"]["content"]

    dados = _extrair_json(conteudo)
    dados["pregador"] = pregador
    dados["data"] = data
    return dados


if __name__ == "__main__":
    exemplo = (
        "Hoje vamos falar sobre vigiar e orar... [cole aqui uma transcrição de teste]"
    )
    resultado = gerar_guia(exemplo, pregador="Pr. Exemplo", data="16 de agosto de 2026")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
