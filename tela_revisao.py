"""
Tela de revisão: mostra o que a IA escreveu, com tudo editável, antes de virar PDF.

Existe porque modelo de linguagem erra — troca a referência bíblica, inventa um
detalhe, entende mal uma palavra da transcrição. O guia vai impresso para as
famílias, então a última palavra é de quem organizou o culto, não do modelo.

Nada aqui chama a IA de novo: o texto já está pronto, isto é só edição. Depois
de confirmar, o PDF sai em poucos segundos.
"""

import tkinter as tk
from tkinter import ttk

import config
import tema


class TelaRevisao(tk.Toplevel):
    def __init__(self, mestre, dados: dict, ao_confirmar, transcricao: str = "",
                 ao_cancelar=None, rotulo_confirmar: str = "Gerar o PDF"):
        super().__init__(mestre)

        self.dados = dict(dados)
        self.ao_confirmar = ao_confirmar
        self.ao_cancelar = ao_cancelar
        self.transcricao = transcricao
        self.confirmou = False
        self.p = tema.paleta()

        self.title("Revisar o guia antes de gerar o PDF")
        self.geometry("820x760")
        self.minsize(700, 560)
        self.configure(bg=tema.FUNDO)
        self.transient(mestre)

        self._montar(rotulo_confirmar)
        self._preencher()

        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.grab_set()

    # ------------------------------------------------------------ construção

    def _montar(self, rotulo_confirmar):
        faixa = tk.Frame(self, bg=self.p["principal"], height=76)
        faixa.pack(fill="x")
        faixa.pack_propagate(False)
        textos = tk.Frame(faixa, bg=self.p["principal"])
        textos.pack(side="left", anchor="w", padx=24, pady=14)
        tk.Label(textos, text="Revise antes de imprimir", bg=self.p["principal"],
                 fg=self.p["sobre_principal"], font=(tema.FONTE, 14, "bold"),
                 ).pack(anchor="w")
        tk.Label(textos, bg=self.p["principal"], fg=self.p["sobre_principal"],
                 font=(tema.FONTE, 9),
                 text="Tudo abaixo pode ser corrigido. A IA às vezes erra a "
                      "referência ou entende mal uma palavra.",
                 ).pack(anchor="w", pady=(2, 0))

        # rodapé antes do corpo: o corpo é expand=True e engoliria o espaço
        rodape = tk.Frame(self, bg=tema.CARTAO,
                          highlightbackground=tema.BORDA, highlightthickness=1)
        rodape.pack(fill="x", side="bottom")
        dentro = tk.Frame(rodape, bg=tema.CARTAO, padx=20, pady=14)
        dentro.pack(fill="x")

        botao = tema.BotaoPrincipal(dentro, rotulo_confirmar, self._confirmar,
                                    cor=self.p["principal"])
        botao.configure(padx=22, pady=10)
        botao.pack(side="right")
        ttk.Button(dentro, text="Cancelar", style="Secundario.TButton",
                   command=self._cancelar).pack(side="right", padx=10)
        if self.transcricao:
            ttk.Button(dentro, text="Ver a transcrição", style="Secundario.TButton",
                       command=self._ver_transcricao).pack(side="left")

        # corpo rolável: o formulário é bem mais alto que qualquer tela
        corpo = tk.Frame(self, bg=tema.FUNDO)
        corpo.pack(fill="both", expand=True)

        self.tela = tk.Canvas(corpo, bg=tema.FUNDO, highlightthickness=0)
        rolagem = ttk.Scrollbar(corpo, orient="vertical", command=self.tela.yview)
        self.tela.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.tela.pack(side="left", fill="both", expand=True)

        self.form = tk.Frame(self.tela, bg=tema.FUNDO, padx=24, pady=18)
        janela = self.tela.create_window((0, 0), window=self.form, anchor="nw")
        self.form.bind(
            "<Configure>",
            lambda _: self.tela.configure(scrollregion=self.tela.bbox("all")))
        # sem isto o formulário fica com a largura mínima e o texto não quebra
        self.tela.bind("<Configure>",
                       lambda e: self.tela.itemconfigure(janela, width=e.width))

        # a roda do mouse só rola esta janela enquanto ela existir
        self.bind_all("<MouseWheel>", self._rolar)
        self.bind("<Destroy>", self._soltar_roda)

    def _rolar(self, evento):
        self.tela.yview_scroll(int(-evento.delta / 120), "units")

    def _soltar_roda(self, evento):
        if evento.widget is self:
            self.unbind_all("<MouseWheel>")

    # ----------------------------------------------------------- ingredientes

    def _secao(self, texto, ajuda=""):
        linha = tk.Frame(self.form, bg=tema.FUNDO)
        linha.pack(fill="x", pady=(18, 6))
        tk.Label(linha, text=texto.upper(), bg=tema.FUNDO, fg=self.p["principal"],
                 font=(tema.FONTE, 9, "bold")).pack(anchor="w")
        tk.Frame(linha, bg=config.COR_DESTAQUE, height=2, width=38).pack(anchor="w",
                                                                       pady=(3, 0))
        if ajuda:
            tk.Label(self.form, text=ajuda, bg=tema.FUNDO, fg=tema.TEXTO_FRACO,
                     font=(tema.FONTE, 8), justify="left", wraplength=640,
                     ).pack(anchor="w", pady=(0, 5))

    def _rotulo(self, texto):
        tk.Label(self.form, text=texto, bg=tema.FUNDO, fg=tema.TEXTO,
                 font=(tema.FONTE, 9, "bold")).pack(anchor="w", pady=(6, 3))

    def _campo(self, valor=""):
        var = tk.StringVar(value=str(valor or ""))
        ttk.Entry(self.form, textvariable=var, style="Campo.TEntry",
                  font=(tema.FONTE, 10)).pack(fill="x")
        return var

    def _area(self, valor="", linhas=4):
        caixa = tk.Text(self.form, height=linhas, wrap="word", relief="flat",
                        font=(tema.FONTE, 10), bg=tema.CARTAO, fg=tema.TEXTO,
                        padx=10, pady=8, highlightthickness=1,
                        highlightbackground=tema.BORDA,
                        highlightcolor=self.p["principal"],
                        insertbackground=tema.TEXTO)
        caixa.pack(fill="x")
        caixa.insert("1.0", str(valor or ""))
        return caixa

    # ------------------------------------------------------------ formulário

    def _preencher(self):
        d = self.dados

        self._secao("Cabeçalho do guia")
        self._rotulo("Tema")
        self.var_tema = self._campo(d.get("tema"))
        self._rotulo("Passagem bíblica")
        self.var_passagem = self._campo(d.get("passagem_biblica"))
        tk.Label(self.form, bg=tema.FUNDO, fg=tema.TEXTO_FRACO, justify="left",
                 font=(tema.FONTE, 8), wraplength=640,
                 text="Confira esta linha com atenção: é o campo que a IA mais "
                      "erra, e ela sai impressa no topo da folha.",
                 ).pack(anchor="w", pady=(3, 0))

        self._rotulo("Pregador")
        self.var_pregador = self._campo(d.get("pregador"))
        self._rotulo("Data")
        self.var_data = self._campo(d.get("data"))

        self._secao("Resumo da mensagem", "Dois parágrafos.")
        resumo = d.get("resumo_mensagem")
        if isinstance(resumo, str):
            resumo = [resumo, ""]
        resumo = list(resumo or ["", ""]) + ["", ""]
        self._rotulo("Primeiro parágrafo")
        self.caixa_resumo1 = self._area(resumo[0], linhas=5)
        self._rotulo("Segundo parágrafo")
        self.caixa_resumo2 = self._area(resumo[1], linhas=5)

        self._secao("Pontos de aprofundamento bíblico")
        self.pontos = []
        pontos = list(d.get("pontos_aprofundamento") or [])
        while len(pontos) < 3:
            pontos.append({"titulo": "", "texto": ""})
        for i, ponto in enumerate(pontos, start=1):
            self._rotulo(f"Ponto {i} — título")
            titulo = self._campo(ponto.get("titulo"))
            self._rotulo(f"Ponto {i} — texto")
            texto = self._area(ponto.get("texto"), linhas=4)
            self.pontos.append((titulo, texto))

        self._secao("Perguntas de aprofundamento",
                    "Três perguntas para aprofundar e praticar a mensagem.")
        self.perguntas = []
        perguntas = list(d.get("perguntas_aprofundamento") or [])
        while len(perguntas) < 3:
            perguntas.append("")
        for i, pergunta in enumerate(perguntas, start=1):
            self._rotulo(f"Pergunta {i}")
            self.perguntas.append(self._area(pergunta, linhas=2))

        self._secao("Oração final")
        self.caixa_oracao = self._area(d.get("oracao_final"), linhas=5)

        hino = d.get("hino_sugerido") or {}
        self._secao("Hino da Harpa Cristã",
                    "O número fica em branco quando não foi conferido — "
                    "escreva o da Harpa da igreja se quiser que apareça no PDF.")
        self._rotulo("Número")
        self.var_hino_numero = self._campo(hino.get("numero"))
        self._rotulo("Título")
        self.var_hino_titulo = self._campo(hino.get("titulo"))
        self._rotulo("Comentário")
        self.caixa_hino = self._area(hino.get("comentario"), linhas=3)

        tk.Frame(self.form, bg=tema.FUNDO, height=10).pack()

    # ---------------------------------------------------------------- ações

    def _texto(self, caixa) -> str:
        return caixa.get("1.0", "end-1c").strip()

    def _coletar(self) -> dict:
        d = dict(self.dados)
        d["tema"] = self.var_tema.get().strip()
        d["passagem_biblica"] = self.var_passagem.get().strip()
        d["pregador"] = self.var_pregador.get().strip()
        d["data"] = self.var_data.get().strip()
        d["resumo_mensagem"] = [p for p in (self._texto(self.caixa_resumo1),
                                            self._texto(self.caixa_resumo2)) if p]

        d["pontos_aprofundamento"] = [
            {"titulo": t.get().strip(), "texto": self._texto(c)}
            for t, c in self.pontos
            if t.get().strip() or self._texto(c)
        ]
        d["perguntas_aprofundamento"] = [
            self._texto(c) for c in self.perguntas if self._texto(c)
        ]
        d["oracao_final"] = self._texto(self.caixa_oracao)

        numero = self.var_hino_numero.get().strip()
        d["hino_sugerido"] = {
            "numero": numero or None,
            "titulo": self.var_hino_titulo.get().strip(),
            "comentario": self._texto(self.caixa_hino),
        }
        return d

    def _confirmar(self):
        self.confirmou = True
        dados = self._coletar()
        self.unbind_all("<MouseWheel>")
        self.grab_release()
        self.destroy()
        self.ao_confirmar(dados)

    def _cancelar(self):
        self.unbind_all("<MouseWheel>")
        self.grab_release()
        self.destroy()
        if self.ao_cancelar:
            self.ao_cancelar()

    def _ver_transcricao(self):
        janela = tk.Toplevel(self)
        janela.title("Transcrição bruta — o que o áudio dizia")
        janela.geometry("720x520")
        janela.configure(bg=tema.FUNDO)
        caixa = tk.Text(janela, wrap="word", font=(tema.FONTE, 10), padx=16,
                        pady=14, bg=tema.CARTAO, fg=tema.TEXTO, relief="flat")
        barra = ttk.Scrollbar(janela, command=caixa.yview)
        caixa.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        caixa.pack(fill="both", expand=True, padx=16, pady=16)
        caixa.insert("1.0", self.transcricao or "(vazio)")
        caixa.config(state="disabled")


if __name__ == "__main__":
    exemplo = {
        "tema": "A Cura da Ansiedade",
        "passagem_biblica": "Filipenses 4:6-7",
        "pregador": "Pr. Exemplo",
        "data": "20 de agosto de 2026",
        "resumo_mensagem": ["Primeiro parágrafo do resumo.",
                            "Segundo parágrafo do resumo."],
        "pontos_aprofundamento": [
            {"titulo": "A oração não é o último recurso", "texto": "Texto do ponto."},
            {"titulo": "Com ações de graças", "texto": "Texto do ponto."},
            {"titulo": "A paz como sentinela", "texto": "Texto do ponto."},
        ],
        "perguntas_aprofundamento": ["Primeira?", "Segunda?", "Terceira?"],
        "oracao_final": "Senhor, entregamos a Ti a nossa ansiedade.",
        "hino_sugerido": {"numero": None, "titulo": "Ó Que Amigo Temos em Cristo",
                          "comentario": "Fala de entregar a aflição a Deus."},
    }

    raiz = tk.Tk()
    raiz.withdraw()
    tema.aplicar_estilos(raiz)
    TelaRevisao(raiz, exemplo, lambda d: (print(d), raiz.quit()),
                transcricao="transcrição de exemplo",
                ao_cancelar=raiz.quit)
    raiz.mainloop()
