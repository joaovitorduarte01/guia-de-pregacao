"""
Gera o harpa_dados.py — os 640 hinos da Harpa Cristã, com número, título e as
palavras que mais identificam cada um.

    python gerar_harpa.py

Roda só quando for preciso regerar a base. O harpa_dados.py fica versionado,
então o programa não depende de internet nem deste script para funcionar.

De onde vêm os dados e por que confiar neles
--------------------------------------------
A base veio de um levantamento público dos 640 hinos, conferida contra duas
outras fontes independentes antes de ser aceita:

- na faixa 1-400, bateu 303/303 com a terceira fonte, sem uma discordância;
- a segunda fonte tinha os hinos 335 a 355 deslocados em uma posição (colocava
  "Mui Perto Está o Dia" no 355, quando ele é o 335) e foi descartada nessa
  faixa por perder 2 a 1;
- de 401 a 640 as fontes concordam na numeração; as poucas diferenças são de
  grafia ("Sois Benvindos" / "Sois Bem-vindos").

Número de hino errado é o pior erro possível aqui: só aparece no meio do culto,
com a família procurando a página. Por isso a conferência cruzada.

As palavras de cada hino saem da letra dele, não de rótulo escrito à mão. Uma
tentativa anterior de listar hinos de cabeça errou 15 dos 23 títulos — inclusive
inventando "Rude Cruz", que não existe na Harpa.
"""

import json
import os
import re
import unicodedata
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "harpa_dados.py")

FONTE = ("https://raw.githubusercontent.com/DanielLiberato/"
         "Harpa-Crista-JSON-640-Hinos-Completa/main/harpa_crista_640_hinos.json")

# Quantas palavras guardar por hino. O bastante para reconhecer o assunto sem
# inchar o arquivo — a letra inteira dos 640 passa de meio megabyte.
PALAVRAS_POR_HINO = 34

# Palavras que aparecem em quase todo hino e por isso não distinguem nenhum,
# mais o feijão com arroz do português.
VAZIAS = set("""
a as o os um uma uns umas de do da dos das em no na nos nas por pra para pelo
pela pelos pelas com sem sob sobre entre ate apos ante e ou mas nem que se quem
qual quais como quando onde porque pois porem entao assim ja nao sim tambem so
somente muito mais menos tao tanto todo toda todos todas cada outro outra outros
outras mesmo mesma este esta estes estas esse essa esses essas aquele aquela
aqueles aquelas isto isso aquilo eu tu ele ela nos vos eles elas me te se lhe
nos vos lhes meu minha meus minhas teu tua teus tuas seu sua seus suas nosso
nossa nossos nossas vosso vossa vossos vossas ser estar ter haver ir vir dar
fazer poder querer saber ver dizer sou es e somos sois sao era eram foi foram
sera serao esta estao estava estavam tem tenho tens temos teem tinha tinham ha
vai vao vou vamos venha vem venho vinde da dao dou damos faz fazem faco fazemos
posso pode podem quero quer querem sei sabe sabem vejo ve veem digo diz dizem
ao aos as la ali aqui ai onde bem mal ainda sempre nunca jamais agora hoje
oh ah eis pois entao porem contudo todavia enquanto embora caso desde
sim nao ne ó
""".split())

# Estas aparecem em tanto hino que casariam com qualquer pregação.
GENERICAS = set("""
deus jesus cristo senhor pai filho espirito santo alma coracao vida amor gloria
louvor cantar cantemos aleluia amem ceu terra mundo homem povo irmao irmaos
graca bencao eterno eterna divino divina celeste bendito santo santa
""".split())


def sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def palavras(texto: str):
    """
    Devolve (chave, exibicao) — a chave é sem acento, para comparar; a exibição
    guarda o acento, porque essas palavras acabam saindo escritas no guia, na
    frase que liga o hino à mensagem.
    """
    texto = re.sub(r"<[^>]+>", " ", str(texto))
    # 3 letras e não 4: "paz", "fé", "luz" e "lar" são dos assuntos que mais
    # aparecem em pregação, e ficavam todos de fora do índice
    for bruto in re.findall(r"[A-Za-zÀ-ÿ]{3,}", texto):
        chave = sem_acento(bruto)
        if chave not in VAZIAS:
            yield chave, bruto.lower()


def baixar() -> dict:
    print(f"baixando {FONTE.rsplit('/', 1)[-1]} ...")
    with urllib.request.urlopen(FONTE, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def extrair(bruto: dict) -> list:
    hinos = []
    for chave, dados in bruto.items():
        if not chave.lstrip("-").isdigit() or int(chave) < 1:
            continue  # a entrada "-1" é a assinatura do autor da base
        numero = int(chave)
        titulo = re.sub(r"^\s*\d+\s*-\s*", "", dados["hino"]).strip()
        letra = " ".join([dados.get("coro", "")]
                         + list(dados.get("verses", {}).values()))
        hinos.append((numero, titulo, letra))
    hinos.sort()
    return hinos


def escolher_palavras(hinos: list) -> dict:
    """
    Fica com as palavras que identificam CADA hino, não as que todo hino tem.

    "coração" aparece em centenas deles e não ajuda a escolher; "sentinela",
    em pouquíssimos, e vale por dez. É a ideia do TF-IDF, na conta mais simples
    que resolve: peso = vezes que aparece aqui ÷ quantos hinos a contêm.
    """
    contagens, em_quantos, acentuada = {}, {}, {}
    for numero, titulo, letra in hinos:
        conta = {}
        for chave, exibicao in palavras(f"{titulo} {letra}"):
            conta[chave] = conta.get(chave, 0) + 1
            acentuada.setdefault(chave, exibicao)
        # o título vale mais: é o que resume o hino
        for chave, _ in palavras(titulo):
            conta[chave] = conta.get(chave, 0) + 4
        contagens[numero] = conta
        for p in conta:
            em_quantos[p] = em_quantos.get(p, 0) + 1

    escolhidas = {}
    for numero, conta in contagens.items():
        pontuadas = [
            (vezes / (em_quantos[p] ** 0.6), p)
            for p, vezes in conta.items()
            if p not in GENERICAS and em_quantos[p] < len(hinos) * 0.25
        ]
        pontuadas.sort(reverse=True)
        escolhidas[numero] = sorted(acentuada[p] for _, p in pontuadas[:PALAVRAS_POR_HINO])
    return escolhidas


def escrever(hinos: list, chaves: dict):
    linhas = [
        '"""',
        "Os 640 hinos da Harpa Cristã: número, título e as palavras que mais",
        "identificam a letra de cada um.",
        "",
        "ARQUIVO GERADO — não edite à mão. Rode o gerar_harpa.py para refazer.",
        '"""',
        "",
        "# (número, título, palavras da letra que identificam o hino)",
        "HINOS = (",
    ]
    for numero, titulo, _ in hinos:
        titulo_py = titulo.replace('"', "'")
        linhas.append(f'    ({numero}, "{titulo_py}", "{" ".join(chaves[numero])}"),')
    linhas.append(")")
    linhas.append("")

    with open(DESTINO, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas))


if __name__ == "__main__":
    hinos = extrair(baixar())
    print(f"{len(hinos)} hinos, do {hinos[0][0]} ao {hinos[-1][0]}")

    faltando = set(range(1, 641)) - {n for n, _, _ in hinos}
    if faltando:
        print(f"ATENÇÃO: faltam os números {sorted(faltando)[:20]}")

    escrever(hinos, escolher_palavras(hinos))
    tamanho = os.path.getsize(DESTINO) / 1024
    print(f"gravado em harpa_dados.py ({tamanho:.0f} KB)")
