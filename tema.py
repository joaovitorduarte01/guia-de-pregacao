"""
Paleta e estilos da interface desktop.

As cores derivam todas de config.COR_PRIMARIA, então quando a pessoa troca a
cor da igreja nas Configurações a interface inteira acompanha — sem precisar
ajustar tom por tom na mão.
"""

import tkinter as tk
from tkinter import ttk

import config

# Neutros fixos: não dependem da cor da igreja
FUNDO = "#F7F6F4"        # fundo da janela, levemente quente
CARTAO = "#FFFFFF"       # fundo dos blocos de conteúdo
BORDA = "#E4E1DC"
TEXTO = "#2B2B2B"
TEXTO_FRACO = "#6B6560"
AVISO_FUNDO = "#FFF6E6"
AVISO_BORDA = "#F0D9AC"
AVISO_TEXTO = "#7A4B00"
SUCESSO = "#1E7A3D"

FONTE = "Segoe UI"


def _rgb(cor_hex: str):
    cor_hex = cor_hex.lstrip("#")
    if len(cor_hex) == 3:
        cor_hex = "".join(c * 2 for c in cor_hex)
    return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(c))) for c in rgb)


def misturar(cor_a: str, cor_b: str, t: float) -> str:
    """t=0 devolve cor_a, t=1 devolve cor_b."""
    a, b = _rgb(cor_a), _rgb(cor_b)
    return _hex(a[i] + (b[i] - a[i]) * t for i in range(3))


def escurecer(cor: str, t: float = 0.15) -> str:
    return misturar(cor, "#000000", t)


def clarear(cor: str, t: float = 0.85) -> str:
    return misturar(cor, "#FFFFFF", t)


def cor_de_texto_sobre(fundo: str) -> str:
    """Branco ou preto, o que tiver mais contraste — a igreja pode escolher
    uma cor clara e o texto branco sumiria."""
    r, g, b = _rgb(fundo)
    luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#1A1A1A" if luminancia > 0.6 else "#FFFFFF"


def paleta():
    principal = config.COR_PRIMARIA
    return {
        "principal": principal,
        "principal_escuro": escurecer(principal, 0.18),
        "principal_claro": clarear(principal, 0.90),
        "sobre_principal": cor_de_texto_sobre(principal),
    }


def aplicar_estilos(raiz: tk.Misc):
    """Configura os widgets ttk. O tema 'clam' é o único que deixa mudar cor
    de verdade no Windows — o padrão ignora quase tudo que a gente pede."""
    p = paleta()
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    estilo.configure(
        "Campo.TEntry",
        fieldbackground=CARTAO, background=CARTAO, foreground=TEXTO,
        bordercolor=BORDA, lightcolor=BORDA, darkcolor=BORDA,
        borderwidth=1, relief="solid", padding=7,
    )
    estilo.map(
        "Campo.TEntry",
        bordercolor=[("focus", p["principal"])],
        lightcolor=[("focus", p["principal"])],
        darkcolor=[("focus", p["principal"])],
    )

    for nome in ("Campo.TCombobox", "Campo.TSpinbox"):
        estilo.configure(
            nome,
            fieldbackground=CARTAO, background=CARTAO, foreground=TEXTO,
            bordercolor=BORDA, lightcolor=BORDA, darkcolor=BORDA,
            arrowcolor=TEXTO_FRACO, borderwidth=1, padding=5,
        )
        estilo.map(nome, bordercolor=[("focus", p["principal"])])

    estilo.configure(
        "Secundario.TButton",
        background=CARTAO, foreground=TEXTO, bordercolor=BORDA,
        lightcolor=BORDA, darkcolor=BORDA, borderwidth=1,
        focusthickness=0, padding=(14, 7), font=(FONTE, 9),
    )
    estilo.map(
        "Secundario.TButton",
        background=[("active", "#F0EEEB")],
        bordercolor=[("active", TEXTO_FRACO)],
    )

    estilo.configure(
        "Barra.Horizontal.TProgressbar",
        troughcolor="#EDEAE6", bordercolor="#EDEAE6",
        background=p["principal"], lightcolor=p["principal"],
        darkcolor=p["principal"], thickness=6,
    )
    return p


class BotaoPrincipal(tk.Label):
    """
    Botão de destaque. É um Label e não um tk.Button porque no Windows o
    Button nativo não deixa pintar o fundo de verdade — ele força o cinza do
    sistema. Com Label a gente controla cor, hover e cursor.
    """

    def __init__(self, mestre, texto, comando, **kw):
        self._cor = kw.pop("cor", config.COR_PRIMARIA)
        self._comando = comando
        self._ativo = True
        super().__init__(
            mestre, text=texto, bg=self._cor, fg=cor_de_texto_sobre(self._cor),
            font=(FONTE, 11, "bold"), pady=12, cursor="hand2", **kw
        )
        self.bind("<Button-1>", self._clicar)
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._sair)

    def _clicar(self, _=None):
        if self._ativo and self._comando:
            self._comando()

    def _entrar(self, _=None):
        if self._ativo:
            self.configure(bg=escurecer(self._cor, 0.15))

    def _sair(self, _=None):
        if self._ativo:
            self.configure(bg=self._cor)

    def definir_cor(self, cor):
        self._cor = cor
        if self._ativo:
            self.configure(bg=cor, fg=cor_de_texto_sobre(cor))

    def habilitar(self, ligado: bool, texto: str = None):
        self._ativo = ligado
        if texto:
            self.configure(text=texto)
        if ligado:
            self.configure(bg=self._cor, fg=cor_de_texto_sobre(self._cor),
                           cursor="hand2")
        else:
            self.configure(bg="#D6D2CC", fg="#8A8580", cursor="watch")
