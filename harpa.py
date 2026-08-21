"""
Hinos da Harpa Cristã para a seção 4 do guia.

Existe por dois motivos:

1. O guia SEMPRE tem que sair com um hino. Quando o modelo devolve o campo
   vazio (acontece), a escolha é feita aqui, por palavra-chave do tema.

2. Modelo de linguagem inventa número de hino com uma segurança impressionante.
   Número errado impresso no guia é o tipo de erro que só aparece na hora do
   culto, com a família tentando achar a página. Por isso o número sugerido
   pelo modelo é DESCARTADO: só sai impresso número que esteja no dicionário
   NUMEROS abaixo, conferido por gente.

Preencha o NUMEROS com a numeração da Harpa que a sua igreja usa e os números
passam a aparecer no PDF. Sem isso o guia mostra só o título — que é o que a
maioria procura no índice mesmo.
"""

import unicodedata

# Título exatamente como sai impresso -> número na Harpa Cristã.
# Deixado vazio de propósito: número que não foi conferido não vai pro papel.
NUMEROS = {
    # "Chuvas de Bênçãos": 1,
}

# Os temas são palavras que aparecem no tema/resumo da pregação. Quanto mais
# palavras baterem, mais o hino combina com a mensagem.
HINOS = (
    {"titulo": "Ó Que Amigo Temos em Cristo",
     "temas": ("ansiedade", "aflição", "oração", "angústia", "preocupação",
               "cansaço", "amigo", "consolo", "peso", "sofrimento")},
    {"titulo": "Doce Oração",
     "temas": ("oração", "súplica", "intercessão", "clamor", "comunhão",
               "buscar", "joelhos")},
    {"titulo": "Deus Cuidará de Ti",
     "temas": ("cuidado", "provisão", "sustento", "necessidade", "confiança",
               "amparo", "pão", "sustenta", "guarda")},
    {"titulo": "Chuvas de Bênçãos",
     "temas": ("bênção", "avivamento", "derramamento", "espírito", "promessa",
               "renovo", "poder")},
    {"titulo": "Conta as Bênçãos",
     "temas": ("gratidão", "agradecer", "ação de graças", "bênção", "lembrar",
               "louvor", "reconhecer")},
    {"titulo": "Saudosa Lembrança",
     "temas": ("cruz", "sacrifício", "ceia", "memória", "entrega", "calvário",
               "amor de deus")},
    {"titulo": "Rude Cruz",
     "temas": ("cruz", "calvário", "sacrifício", "redenção", "salvação",
               "sangue", "morte de cristo")},
    {"titulo": "Alvo Mais que a Neve",
     "temas": ("perdão", "arrependimento", "pecado", "purificação", "limpeza",
               "restauração", "confissão")},
    {"titulo": "Grandioso És Tu",
     "temas": ("adoração", "criação", "majestade", "grandeza", "louvor",
               "poder de deus", "soberania")},
    {"titulo": "Santo, Santo, Santo",
     "temas": ("santidade", "adoração", "reverência", "culto", "glória",
               "trono", "santo")},
    {"titulo": "Castelo Forte",
     "temas": ("proteção", "refúgio", "batalha", "luta", "inimigo", "medo",
               "fortaleza", "guerra espiritual", "vitória")},
    {"titulo": "Firme nas Promessas",
     "temas": ("promessa", "fé", "firmeza", "palavra", "confiança",
               "fidelidade", "esperar", "prova")},
    {"titulo": "Que Segurança",
     "temas": ("segurança", "certeza", "salvação", "testemunho", "alegria",
               "garantia")},
    {"titulo": "Mais Perto Quero Estar",
     "temas": ("intimidade", "comunhão", "presença", "buscar", "achegar",
               "devocional", "relacionamento com deus")},
    {"titulo": "Vencendo Vem Jesus",
     "temas": ("volta de cristo", "vinda", "esperança", "vigiar", "vigilância",
               "arrebatamento", "vitória", "segunda vinda", "preparo")},
    {"titulo": "Achei um Bom Amigo",
     "temas": ("amizade", "encontro com cristo", "salvação", "alegria",
               "conversão", "testemunho")},
    {"titulo": "Grande Gozo Tenho Eu",
     "temas": ("alegria", "gozo", "júbilo", "salvação", "felicidade",
               "contentamento")},
    {"titulo": "Trabalhai, Trabalhai",
     "temas": ("serviço", "obra", "trabalho", "missão", "evangelização",
               "seara", "chamado", "ide")},
    {"titulo": "Vem a Jesus",
     "temas": ("convite", "salvação", "arrependimento", "decisão", "conversão",
               "chamado", "perdido")},
    {"titulo": "Ao Deus de Abraão Louvai",
     "temas": ("fidelidade", "aliança", "adoração", "louvor", "geração",
               "herança", "família")},
    {"titulo": "Tudo Entregarei",
     "temas": ("consagração", "entrega", "rendição", "obediência", "sacrifício",
               "submissão", "senhorio")},
    {"titulo": "Bendito Seja o Cordeiro",
     "temas": ("redenção", "cordeiro", "sangue", "adoração", "salvação",
               "louvor")},
    {"titulo": "Porque Ele Vive",
     "temas": ("esperança", "ressurreição", "futuro", "vida", "medo do amanhã",
               "vitória sobre a morte", "cristo vive")},
)

# Quando nada bate, o hino sai daqui — todos servem para qualquer mensagem.
# A escolha varia com o tema pra não repetir o mesmo hino toda semana.
GERAIS = ("Grandioso És Tu", "Firme nas Promessas", "Chuvas de Bênçãos",
          "Mais Perto Quero Estar", "Conta as Bênçãos")


def _normalizar(texto: str) -> str:
    """minúsculas e sem acento, pra comparar título digitado de qualquer jeito"""
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


_POR_TITULO = {_normalizar(h["titulo"]): h for h in HINOS}

# Os dois lados da comparação precisam estar sem acento. Comparar o tema já
# normalizado contra "bênção" faria toda palavra acentuada da lista — que são
# quase todas — nunca casar, e a escolha cairia sempre nos hinos gerais.
_TEMAS = {h["titulo"]: tuple(_normalizar(t) for t in h["temas"]) for h in HINOS}


def buscar(titulo: str):
    """Devolve o hino da lista se o título for um hino conhecido, senão None."""
    return _POR_TITULO.get(_normalizar(titulo).strip())


def _pontuar(hino: dict, texto: str) -> int:
    return sum(1 for t in _TEMAS[hino["titulo"]] if t in texto)


def _comentario_padrao(hino: dict) -> str:
    temas = [t for t in hino["temas"][:3] if " " not in t] or list(hino["temas"][:2])
    assunto = " e ".join(temas[:2])
    return (f"Fala de {assunto} — combina com o que foi pregado. "
            "Boa opção para cantar em família antes de começar o estudo.")


def escolher(tema: str = "", resumo: str = "", sugestao: dict = None) -> dict:
    """
    Devolve sempre um hino da Harpa, no formato que o template espera.

    `sugestao` é o que o modelo respondeu. O título é aproveitado quando
    corresponde a um hino conhecido; o número, nunca — veja o topo do arquivo.
    """
    sugestao = sugestao if isinstance(sugestao, dict) else {}
    escolhido = buscar(sugestao.get("titulo", ""))
    comentario = str(sugestao.get("comentario") or "").strip()

    if escolhido is None:
        texto = _normalizar(f"{tema} {resumo}")
        candidatos = sorted(HINOS, key=lambda h: -_pontuar(h, texto))

        if _pontuar(candidatos[0], texto) > 0:
            escolhido = candidatos[0]
        else:
            # nada bateu: escolhe um dos gerais, variando conforme o tema
            indice = sum(ord(c) for c in _normalizar(tema)) % len(GERAIS)
            escolhido = buscar(GERAIS[indice])

        # o comentário do modelo falava de outro hino — não serve mais
        comentario = ""

    return {
        "numero": NUMEROS.get(escolhido["titulo"]),
        "titulo": escolhido["titulo"],
        "comentario": comentario or _comentario_padrao(escolhido),
    }


if __name__ == "__main__":
    exemplos = [
        ("A Cura da Ansiedade", "Paulo ensina a entregar a ansiedade a Deus pela oração."),
        ("Vigiai e Orai", "Jesus adverte sobre a sua volta e pede vigilância."),
        ("O Preço da Cruz", "O sacrifício do Calvário e o perdão dos pecados."),
        ("Tema Sem Palavra Conhecida", "Texto qualquer sem gancho nenhum."),
    ]
    for tema, resumo in exemplos:
        h = escolher(tema, resumo)
        print(f"{tema:34} -> {h['titulo']}")
