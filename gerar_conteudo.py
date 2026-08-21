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

O que o modelo devolve NÃO é aceito como veio. Tem uma etapa de conferência
(`_arrumar`) que garante o que o guia precisa ter sempre: resumo em dois
parágrafos, três pontos, três perguntas e um hino da Harpa. Modelo pequeno
esquece regra, e o guia é impresso e entregue às famílias.
"""

import json
import re

import requests

import config
import harpa

# O que o Ollama usa por padrão. Dá para aumentar, mas cada token a mais custa
# memória, e em máquina apertada isso derruba a velocidade mais do que ajuda.
CONTEXTO = 4096
RESERVA_RESPOSTA = 1000   # espaço que a resposta do modelo vai ocupar
RESERVA_INSTRUCOES = 900  # espaço do PROMPT_SISTEMA

# Sobra para o texto da pregação em cada chamada
ESPACO_TEXTO = CONTEXTO - RESERVA_RESPOSTA - RESERVA_INSTRUCOES

# Português rende ~3,5 caracteres por token. Estimativa grosseira de propósito:
# errar para menos é seguro, errar para mais faria o modelo cortar conteúdo.
CARACTERES_POR_TOKEN = 3.5

# Quantos itens o guia sempre tem
QUANTOS_PONTOS = 3
QUANTAS_PERGUNTAS = 3

PROMPT_SISTEMA = """\
Você é um assistente que transforma a transcrição de uma pregação em um \
GUIA DE ESTUDO EM FAMÍLIA, em português do Brasil, seguindo EXATAMENTE esta \
estrutura em JSON (responda SOMENTE o JSON, sem markdown, sem texto antes ou depois):

{
  "tema": "título curto e impactante da pregação",
  "passagem_biblica": "ex: Filipenses 4:6-7",
  "resumo_mensagem": ["primeiro parágrafo do resumo", "segundo parágrafo do resumo"],
  "pontos_aprofundamento": [
    {"titulo": "título curto do ponto", "texto": "parágrafo que aprofunda o ensino bíblico do ponto e mostra como vivê-lo"}
  ],
  "perguntas_aprofundamento": [
    "uma pergunta que leve a família a aprofundar e praticar a mensagem, escrita por extenso"
  ],
  "oracao_final": "oração de 3 a 5 frases relacionada ao tema, em primeira pessoa do plural (nós)",
  "hino_sugerido": {
    "titulo": "título de um hino da Harpa Cristã que combine com o tema",
    "comentario": "uma ou duas frases relacionando o hino ao tema"
  }
}

Regras importantes:
- Use APENAS o conteúdo da transcrição como base. Não invente doutrina nem versículos que não foram citados.
- PASSAGEM BÍBLICA: copie a referência EXATAMENTE como o pregador a anunciou na
  transcrição, mesmo que ele diga por extenso ("Filipenses capítulo 4 versículo
  6 e 7" vira "Filipenses 4:6-7"). NÃO troque por outro versículo que combine
  com o tema — este é o erro mais comum e o mais grave, porque a referência sai
  impressa no cabeçalho do guia. Se o pregador não anunciar nenhuma passagem,
  deixe o campo como null.
- RESUMO: exatamente DOIS parágrafos, dois itens no array. O primeiro apresenta
  a mensagem central e o texto bíblico; o segundo desenvolve o que o pregador
  ensinou e onde isso toca a vida da família.
- Os arrays acima mostram UM item de exemplo cada. Gere exatamente 3 pontos de
  aprofundamento e 3 perguntas, todos preenchidos com conteúdo real — nunca
  repita o texto de exemplo nem escreva reticências.
- PERGUNTAS: são de aprofundamento e prática espiritual. Devem levar a família
  a examinar a própria vida e a decidir um passo concreto, não a repetir o que
  ouviu. Escreva por extenso, sem numerar ("Pergunta 1:" está errado).
- ORAÇÃO: escreva a oração de verdade, falando com Deus, de 3 a 5 frases.
  Uma frase só ("vamos orar") não serve.
- HINO: escreva só o TÍTULO de um hino da Harpa Cristã que combine com a
  mensagem. Não escreva número — o número é conferido depois, aqui do lado.
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

# Último recurso, se nem a segunda tentativa trouxer as três perguntas. São
# genéricas de propósito: servem para qualquer mensagem e é melhor entregar o
# guia completo do que uma seção pela metade.
PERGUNTAS_RESERVA = (
    "O que desta mensagem Deus falou mais forte ao seu coração hoje?",
    "Que passo concreto a nossa família pode dar esta semana para viver o que ouvimos?",
    "Por quem podemos orar esta semana, levando essa mesma palavra a essa pessoa?",
)

# O modelo às vezes responde com os nomes antigos dos campos. Aceitar os dois
# custa três linhas e evita um guia vazio.
APELIDOS = {
    "pontos_aplicacao": "pontos_aprofundamento",
    "pontos_de_aprofundamento": "pontos_aprofundamento",
    "perguntas_discussao": "perguntas_aprofundamento",
    "perguntas_de_aprofundamento": "perguntas_aprofundamento",
    "resumo": "resumo_mensagem",
    "hino": "hino_sugerido",
}


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


# ------------------------------------------------------------- conferência

def dois_paragrafos(valor) -> list:
    """
    O resumo sempre sai em dois parágrafos.

    O modelo devolve isso de três jeitos diferentes conforme o humor: array com
    dois itens, array com um, ou um texto corrido. Quando vem tudo junto, o
    corte é feito aqui, na frase mais perto do meio — parágrafo único de doze
    linhas é exatamente o que ninguém lê.
    """
    if isinstance(valor, (list, tuple)):
        partes = [str(p).strip() for p in valor if str(p).strip()]
    else:
        partes = [p.strip() for p in re.split(r"\n\s*\n", str(valor or "")) if p.strip()]

    if len(partes) >= 2:
        # mais de dois: o resto vira o segundo parágrafo, para não perder texto
        return [partes[0], " ".join(partes[1:])]

    if not partes:
        return ["", ""]

    texto = partes[0]
    frases = re.split(r"(?<=[.!?])\s+", texto)
    if len(frases) < 2:
        return [texto, ""]

    metade = len(texto) / 2
    primeiro, acumulado = [], 0
    for i, frase in enumerate(frases):
        primeiro.append(frase)
        acumulado += len(frase) + 1
        # para no primeiro fim de frase que passa da metade, desde que sobre
        # frase para o segundo parágrafo
        if acumulado >= metade and i < len(frases) - 1:
            break

    corte = len(primeiro)
    return [" ".join(frases[:corte]).strip(), " ".join(frases[corte:]).strip()]


def _pedir_itens(material: str, instrucao: str, quantidade: int) -> list:
    """Chamada curta pedindo só um campo que voltou faltando."""
    try:
        bruto = _conversar(
            [
                {"role": "system",
                 "content": (f"Responda SOMENTE um JSON no formato "
                             f'{{"itens": [...]}} com exatamente {quantidade} '
                             f"itens, em português do Brasil. {instrucao}")},
                {"role": "user", "content": material},
            ],
            formato_json=True,
        )
        itens = _extrair_json(bruto).get("itens")
        return list(itens) if isinstance(itens, list) else []
    except (requests.RequestException, ValueError, AttributeError, KeyError):
        # completar um campo é melhor esforço: se falhar, segue com o que tem
        return []


def _pontos_validos(bruto) -> list:
    """Fica só com os pontos que têm título e texto de verdade."""
    limpos = []
    for p in bruto if isinstance(bruto, list) else []:
        if isinstance(p, dict):
            titulo = str(p.get("titulo") or "").strip()
            texto = str(p.get("texto") or "").strip()
        else:
            titulo, texto = "", str(p).strip()
        if texto:
            limpos.append({"titulo": titulo or "Para aprofundar", "texto": texto})
    return limpos


def _perguntas_validas(bruto) -> list:
    limpas = []
    for q in bruto if isinstance(bruto, list) else []:
        if isinstance(q, dict):
            q = q.get("pergunta") or q.get("texto") or ""
        texto = str(q).strip()
        # "Pergunta 1: ..." aparece de vez em quando apesar da instrução
        texto = re.sub(r"^(pergunta\s*)?\d+[\.\)\:\-]\s*", "", texto, flags=re.I)
        if texto:
            limpas.append(texto)
    return limpas


def _arrumar(dados: dict, material: str) -> dict:
    """
    Garante o que o guia sempre precisa ter. Cada seção que faltar ganha uma
    segunda chance com uma chamada curta antes de cair no plano B.
    """
    for antigo, novo in APELIDOS.items():
        if antigo in dados and novo not in dados:
            dados[novo] = dados.pop(antigo)

    dados["resumo_mensagem"] = dois_paragrafos(dados.get("resumo_mensagem"))

    pontos = _pontos_validos(dados.get("pontos_aprofundamento"))
    if len(pontos) < QUANTOS_PONTOS:
        pontos += _pontos_validos(_pedir_itens(
            material,
            'Cada item é um objeto {"titulo": "...", "texto": "..."} com um ponto '
            "de aprofundamento bíblico tirado desta pregação.",
            QUANTOS_PONTOS,
        ))
    dados["pontos_aprofundamento"] = pontos[:QUANTOS_PONTOS]

    perguntas = _perguntas_validas(dados.get("perguntas_aprofundamento"))
    if len(perguntas) < QUANTAS_PERGUNTAS:
        perguntas += _perguntas_validas(_pedir_itens(
            material,
            "Cada item é uma pergunta, em texto, para a família aprofundar e "
            "praticar esta mensagem. Sem numerar.",
            QUANTAS_PERGUNTAS,
        ))
    for reserva in PERGUNTAS_RESERVA:
        if len(perguntas) >= QUANTAS_PERGUNTAS:
            break
        perguntas.append(reserva)
    dados["perguntas_aprofundamento"] = perguntas[:QUANTAS_PERGUNTAS]

    # Só o tema e o resumo entram na escolha do hino. Jogar os pontos junto
    # foi testado e piorou: eles carregam as ILUSTRAÇÕES da pregação, e o
    # "soldado montando guarda na porta da cidade" puxava o hino para "cidade"
    # em vez de ansiedade. O resumo é a mensagem destilada.
    dados["hino_sugerido"] = harpa.escolher(
        tema=dados.get("tema", ""),
        resumo=" ".join(dados["resumo_mensagem"]),
        sugestao=dados.get("hino_sugerido"),
    )

    dados["oracao_final"] = str(dados.get("oracao_final") or "").strip()
    dados["tema"] = str(dados.get("tema") or "Guia de Estudo em Família").strip()
    return dados


# ------------------------------------------------------------------ geração

def gerar_guia(transcricao: str, pregador: str, data: str, progresso=None,
               passagem: str = None) -> dict:
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

    avisar(0.95, "Conferindo o que a IA escreveu...")
    dados = _arrumar(_extrair_json(conteudo), material)

    dados["pregador"] = pregador
    dados["data"] = data

    # Passagem digitada à mão manda. Os modelos erram muito este campo: mesmo
    # com a referência dita com todas as letras na transcrição, trocam por
    # outro versículo do mesmo tema — e ela vai impressa no cabeçalho do guia.
    if passagem and passagem.strip():
        dados["passagem_biblica"] = passagem.strip()

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
        texto, pregador="Pr. Exemplo", data="20 de agosto de 2026",
        progresso=lambda f, t: print(f"  [{f * 100:3.0f}%] {t}"),
    )
    print()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
