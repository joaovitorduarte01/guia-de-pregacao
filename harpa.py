"""
Escolhe o hino da Harpa Cristã que fecha o guia — sempre com número e título.

A base são os 640 hinos de verdade (harpa_dados.py, gerado pelo gerar_harpa.py),
com as palavras que identificam a letra de cada um. A escolha compara o tema e o
resumo da pregação com essas palavras: uma mensagem sobre perdão cai num hino
que fala de perdão, porque a LETRA dele fala disso — não porque alguém rotulou.

O número nunca vem do modelo de IA. Ele inventa número com uma segurança
impressionante, e número errado só aparece no meio do culto, com a família
procurando a página. O que a IA sugere é só o título; o número sai da base.

Uma versão anterior deste arquivo tinha 23 hinos escritos de memória. Quando a
Harpa de verdade chegou, 15 dos 23 títulos não existiam — inclusive "Rude Cruz",
que nunca esteve na Harpa. É por isso que nada aqui é escrito à mão.
"""

import re
import unicodedata

import harpa_dados

# Quando nada na pregação casa com nada, o hino sai daqui. Todos servem para
# qualquer mensagem, e a escolha varia com o tema pra não repetir toda semana.
GERAIS = (1, 107, 526, 545, 564)

# Palavras que aparecem no texto de qualquer pregação sem dizer do que ela
# trata. Sem esta lista o resumo "Paulo ENSINA a ENTREGAR a ansiedade" casava
# com um hino por causa de "ensina" e "entregar" — os verbos da minha frase,
# não o assunto da mensagem.
VAZIAS = set("""
para com sem por que quem qual como quando onde porque pois nao sim tambem
todo toda todos todas cada outro outra este esta esse essa aquele aquela
nosso nossa nossos nossas seu sua seus suas meu minha teu tua
ser estar ter haver fazer poder querer saber dizer mais menos muito
deus jesus cristo senhor vida mundo hoje ainda sempre nunca
nenhum nenhuma algum alguma alguns algumas tudo nada coisa coisas
gente pessoa pessoas vezes modo forma parte lugar caso jeito
qualquer qualquer outra mesma proprio propria
sobre entre depois antes durante desde ate assim entao porem
ensina ensinar fala falar falou disse dizer diz mostra mostrar
pede pedir precisa precisar quer querer vamos temos deve devemos
pregacao pregador mensagem texto versiculo capitulo palavra igreja culto
""".split())


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _palavras(texto: str) -> set:
    return {p for p in re.findall(r"[a-z]{4,}", _sem_acento(texto))
            if p not in VAZIAS}


def _raiz(palavra: str) -> str:
    """
    Corta a palavra no radical grosseiro.

    A pregação fala em "ansiedade" e o hino canta "ansioso"; sem isso as duas
    não se encontram. Quatro letras é o que faz esse par se achar — com cinco,
    "ansie" e "ansio" continuam passando longe.

    Só vale para palavra de 6 letras pra cima. Cortando as curtas, "preço"
    virava "prec" e casava com "precisamos" — foi assim que uma pregação sobre
    a cruz recebeu o hino "Precisamos de Jesus".
    """
    return palavra[:4] if len(palavra) >= 6 else palavra


_POR_NUMERO = {}
_POR_TITULO = {}
_RAIZES = {}

for _numero, _titulo, _palavras_hino in harpa_dados.HINOS:
    _lista = _palavras_hino.split()
    _POR_NUMERO[_numero] = (_titulo, _lista)
    _POR_TITULO.setdefault(_sem_acento(_titulo), _numero)
    _RAIZES[_numero] = {_raiz(_sem_acento(p)) for p in _lista}


def total() -> int:
    return len(_POR_NUMERO)


def por_numero(numero) -> dict:
    """O hino de um número, ou None se o número não existir na Harpa."""
    try:
        numero = int(str(numero).strip())
    except (TypeError, ValueError):
        return None
    if numero not in _POR_NUMERO:
        return None
    return {"numero": numero, "titulo": _POR_NUMERO[numero][0]}


def buscar_titulo(titulo: str):
    """
    Acha o número de um hino pelo título.

    Tenta a igualdade primeiro e depois a comparação por palavras, porque a IA
    escreve o título de qualquer jeito: "O Melhor Amigo" para
    "Jesus, o Melhor Amigo", com ou sem acento, com ou sem vírgula.
    """
    limpo = _sem_acento(titulo).strip()
    if not limpo:
        return None
    if limpo in _POR_TITULO:
        return _POR_TITULO[limpo]

    procuradas = {p for p in re.findall(r"[a-z]{3,}", limpo) if p not in VAZIAS}
    if not procuradas:
        return None

    melhor, nota_melhor = None, 0.0
    for numero, (titulo_real, _) in _POR_NUMERO.items():
        do_hino = {p for p in re.findall(r"[a-z]{3,}", _sem_acento(titulo_real))
                   if p not in VAZIAS}
        if not do_hino:
            continue
        comuns = procuradas & do_hino
        if not comuns:
            continue
        # proporção sobre os dois lados: evita casar "Jesus, o Bom Amigo" com
        # "Amigo" só porque uma palavra bate
        nota = len(comuns) / max(len(procuradas), len(do_hino))
        if nota > nota_melhor:
            melhor, nota_melhor = numero, nota

    return melhor if nota_melhor >= 0.7 else None


def _casar(palavras_hino: list, procuradas: set):
    """
    Quantos ASSUNTOS da pregação o hino cobre, e com que palavras.

    A conta é por palavra da pregação, não por palavra do hino. Sem isso um
    hino que repete "cura, curado, curar" somava três pontos por um assunto só
    e passava na frente de outro que tocava três assuntos diferentes.

    Palavra inteira vale o dobro do radical: "perdão" no hino e "perdão" na
    pregação é mais forte que "perdão" e "perdoar".
    """
    do_hino = {_sem_acento(p): p for p in palavras_hino}
    por_raiz = {}
    for chave, original in do_hino.items():
        por_raiz.setdefault(_raiz(chave), original)

    nota, achadas = 0, []
    for procurada in sorted(procuradas):
        if procurada in do_hino:
            nota += 2
            achadas.append(do_hino[procurada])
        elif _raiz(procurada) in por_raiz:
            nota += 1
            achadas.append(por_raiz[_raiz(procurada)])
    return nota, achadas


def _pontuar(numero: int, procuradas: set):
    """
    Nota do hino para esta pregação.

    O tema e o resumo entram no mesmo saco, com o mesmo peso. Dar mais peso ao
    tema parecia óbvio e foi testado: piorou. Título de pregação é poético e
    tem três palavras de conteúdo — com o tema pesando dez vezes, "O Perdão que
    Restaura" caía em "Pronto a Salvar"; com os dois iguais, cai em "Vem, ó
    Pródigo". O conteúdo está no resumo.
    """
    _, palavras_hino = _POR_NUMERO[numero]
    return _casar(palavras_hino, procuradas)


def _comentario(achadas: list) -> str:
    if not achadas:
        return "Um hino conhecido, que cabe bem no encerramento do estudo."
    assuntos = " e ".join(achadas[:2])
    return (f"A letra fala de {assuntos} — os mesmos assuntos da mensagem. "
            "Boa opção para cantar em família.")


def escolher(tema: str = "", resumo: str = "", sugestao: dict = None) -> dict:
    """
    Devolve sempre um hino existente na Harpa, com número e título conferidos.

    `sugestao` é o que o modelo respondeu. O título dele é aproveitado quando
    corresponde a um hino de verdade; o número dele é sempre ignorado.
    """
    sugestao = sugestao if isinstance(sugestao, dict) else {}
    numero = buscar_titulo(str(sugestao.get("titulo") or ""))
    comentario = str(sugestao.get("comentario") or "").strip()

    if numero is None:
        procuradas = _palavras(f"{tema} {resumo}")

        melhor, nota_melhor, achadas_melhor = None, 0, []
        for candidato in _POR_NUMERO:
            nota, achadas = _pontuar(candidato, procuradas)
            # duas palavras no mínimo: uma só é coincidência, não assunto
            if nota > nota_melhor and len(achadas) >= 2:
                melhor, nota_melhor, achadas_melhor = candidato, nota, achadas

        if melhor is None:
            indice = sum(ord(c) for c in _sem_acento(tema)) % len(GERAIS)
            melhor, achadas_melhor = GERAIS[indice], []

        numero = melhor
        # o comentário do modelo falava de outro hino — não serve mais
        comentario = _comentario(achadas_melhor)

    return {
        "numero": numero,
        "titulo": _POR_NUMERO[numero][0],
        "comentario": comentario or _comentario([]),
    }


if __name__ == "__main__":
    print(f"{total()} hinos na base\n")
    exemplos = [
        ("A Cura da Ansiedade",
         "Paulo ensina a entregar a ansiedade a Deus pela oração, e a paz guarda o coração."),
        ("Vigiai e Orai",
         "Jesus adverte sobre a sua volta e pede vigilância ao povo que espera."),
        ("O Preço da Cruz",
         "O sacrifício do calvário, o sangue derramado e o perdão dos pecados."),
        ("Gratidão em Tudo",
         "Precisamos agradecer e lembrar das bênçãos que já recebemos."),
        ("A Família no Altar",
         "O culto doméstico, os filhos e o lar entregues ao Senhor."),
        ("Quando a Tempestade Vem",
         "O barco no meio do mar, o medo dos discípulos e a calma que Jesus traz."),
        ("Tema Sem Gancho Nenhum", "Texto qualquer."),
    ]
    for tema, resumo in exemplos:
        h = escolher(tema, resumo)
        print(f"{tema:28} -> {h['numero']:3} {h['titulo']}")
        print(f"{'':28}    {h['comentario']}")
