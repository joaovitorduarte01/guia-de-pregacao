"""
Desenha o ícone do aplicativo (static/icone.ico) a partir das cores do config.

É um script e não um .ico solto no repositório pra dar pra refazer quando a
igreja trocar de cor — é só rodar de novo:

    python fazer_icone.py

O desenho é uma Bíblia aberta com uma chama, puxando o lema da igreja
("a chama não pode apagar"). Proposital que seja simples: ícone tem que ser
legível a 16x16 na barra de tarefas, e detalhe demais vira borrão nesse tamanho.
"""

import os

from PIL import Image, ImageDraw

import config

LADO = 512  # desenha grande e reduz — fica com a borda mais limpa
TAMANHOS = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def _mistura(cor_hex, outra_hex, t):
    a = tuple(int(cor_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(outra_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def desenhar() -> Image.Image:
    fundo = config.COR_PRIMARIA
    ouro = config.COR_DESTAQUE
    papel = "#F7F5F0"

    img = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fundo arredondado
    d.rounded_rectangle([0, 0, LADO, LADO], radius=int(LADO * 0.22), fill=fundo)

    # --- a Bíblia aberta -----------------------------------------------
    meio = LADO // 2
    topo = int(LADO * 0.42)
    base = int(LADO * 0.76)
    borda = int(LADO * 0.13)
    curva = int(LADO * 0.045)   # o quanto as páginas "afundam" no centro

    pagina_esq = [
        (borda, topo + curva),
        (meio - int(LADO * 0.012), topo),
        (meio - int(LADO * 0.012), base - curva),
        (borda, base),
    ]
    pagina_dir = [
        (meio + int(LADO * 0.012), topo),
        (LADO - borda, topo + curva),
        (LADO - borda, base),
        (meio + int(LADO * 0.012), base - curva),
    ]
    d.polygon(pagina_esq, fill=papel)
    d.polygon(pagina_dir, fill=papel)

    # sombra suave na dobra central, pra dar volume
    d.line([(meio, topo + int(curva * 0.4)), (meio, base - int(curva * 0.4))],
           fill=_mistura(papel, fundo, 0.35), width=int(LADO * 0.018))

    # linhas de texto — poucas e grossas, senão somem no tamanho pequeno
    cinza = _mistura(papel, fundo, 0.42)
    altura_linha = int(LADO * 0.052)
    y = topo + int(LADO * 0.055)
    for i in range(3):
        recuo = int(LADO * 0.035)
        fim_esq = meio - int(LADO * 0.045) - (i * int(LADO * 0.018))
        d.line([(borda + recuo, y), (fim_esq, y)],
               fill=cinza, width=int(LADO * 0.017))
        inicio_dir = meio + int(LADO * 0.045)
        d.line([(inicio_dir, y), (LADO - borda - recuo - (i * int(LADO * 0.018)), y)],
               fill=cinza, width=int(LADO * 0.017))
        y += altura_linha

    # --- a chama --------------------------------------------------------
    cx = meio
    base_chama = int(LADO * 0.40)
    topo_chama = int(LADO * 0.13)
    largura = int(LADO * 0.105)

    corpo = [
        (cx, topo_chama),
        (cx + largura, base_chama - int(LADO * 0.10)),
        (cx + int(largura * 0.82), base_chama),
        (cx - int(largura * 0.82), base_chama),
        (cx - largura, base_chama - int(LADO * 0.10)),
    ]
    d.polygon(corpo, fill=ouro)

    # núcleo mais claro, pra chama não ficar um borrão chapado
    nucleo = [
        (cx, topo_chama + int(LADO * 0.075)),
        (cx + int(largura * 0.5), base_chama - int(LADO * 0.075)),
        (cx, base_chama - int(LADO * 0.012)),
        (cx - int(largura * 0.5), base_chama - int(LADO * 0.075)),
    ]
    d.polygon(nucleo, fill=_mistura(config.COR_DESTAQUE, "#FFFFFF", 0.55))

    return img


def desenhar_simples() -> Image.Image:
    """
    Versão para 16x16 e 32x32. O desenho completo vira borrão nesse tamanho —
    as linhas de texto somem e o livro fica ilegível. Aqui fica só a chama,
    grande e cheia, que é a parte reconhecível e casa com o lema da igreja.
    """
    fundo = config.COR_PRIMARIA
    ouro = config.COR_DESTAQUE

    img = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, LADO, LADO], radius=int(LADO * 0.22), fill=fundo)

    cx = LADO // 2
    topo = int(LADO * 0.16)
    base = int(LADO * 0.82)
    larg = int(LADO * 0.26)

    d.polygon([
        (cx, topo),
        (cx + larg, base - int(LADO * 0.26)),
        (cx + int(larg * 0.86), base),
        (cx - int(larg * 0.86), base),
        (cx - larg, base - int(LADO * 0.26)),
    ], fill=ouro)

    d.polygon([
        (cx, topo + int(LADO * 0.20)),
        (cx + int(larg * 0.48), base - int(LADO * 0.20)),
        (cx, base - int(LADO * 0.04)),
        (cx - int(larg * 0.48), base - int(LADO * 0.20)),
    ], fill=_mistura(ouro, "#FFFFFF", 0.6))

    return img


def _montar_ico(destino, imagens_por_tamanho):
    """
    Escreve o .ico na mão. O save do Pillow só sabe reduzir UMA imagem para
    todos os tamanhos, e aqui a graça é justamente usar desenhos diferentes
    para os tamanhos pequenos. O formato aceita PNG embutido desde o Vista.
    """
    import io
    import struct

    payloads = []
    for lado, imagem in sorted(imagens_por_tamanho.items()):
        buffer = io.BytesIO()
        imagem.resize((lado, lado), Image.LANCZOS).save(buffer, format="PNG")
        payloads.append((lado, buffer.getvalue()))

    cabecalho = struct.pack("<HHH", 0, 1, len(payloads))  # reservado, tipo=ícone, qtd
    deslocamento = len(cabecalho) + 16 * len(payloads)

    diretorio = b""
    for lado, dados in payloads:
        diretorio += struct.pack(
            "<BBBBHHII",
            0 if lado >= 256 else lado,   # 0 significa 256
            0 if lado >= 256 else lado,
            0, 0, 1, 32,
            len(dados), deslocamento,
        )
        deslocamento += len(dados)

    with open(destino, "wb") as f:
        f.write(cabecalho)
        f.write(diretorio)
        for _, dados in payloads:
            f.write(dados)


def main():
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, "icone.ico")

    completo = desenhar()
    simples = desenhar_simples()

    _montar_ico(destino, {
        16: simples, 24: simples, 32: simples,
        48: completo, 64: completo, 128: completo, 256: completo,
    })

    # PNG junto, útil pro atalho e pra qualquer outro uso
    completo.resize((256, 256), Image.LANCZOS).save(
        os.path.join(pasta, "icone.png"), format="PNG")

    print(f"ícone gerado: {destino}")
    print("  16-32 px: só a chama (o desenho completo some nesse tamanho)")
    print("  48+ px:   Bíblia aberta com a chama")
    return destino


if __name__ == "__main__":
    main()
