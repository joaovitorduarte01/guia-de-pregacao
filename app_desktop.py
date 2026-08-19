"""
Guia de Pregação — aplicativo desktop.

Interface nativa em tkinter (já vem com o Python, não instala nada) no lugar do
Streamlit. Rode com:  python app_desktop.py

O trabalho pesado roda numa thread separada e conversa com a interface por uma
fila — se rodasse na thread da interface, a janela congelaria durante os 5 a 15
minutos de transcrição e o Windows mostraria "não está respondendo".
"""

import os
import queue
import subprocess
import sys
import threading
import traceback
from datetime import date, datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
import tema

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

FORMATOS_AUDIO = [
    ("Áudio", "*.mp3 *.wav *.m4a *.ogg *.aac *.flac *.wma *.opus"),
    ("Todos os arquivos", "*.*"),
]


def formatar_data(d: date) -> str:
    """
    "19 de agosto de 2026" — na mão de propósito: strftime("%B") depende do
    locale do sistema e no Windows sai em inglês ("August").
    """
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def pasta_de_saida() -> str:
    """
    Empacotado como .exe o programa pode estar em Program Files, onde não se
    pode escrever. Então os PDFs vão para os Documentos do usuário.
    """
    documentos = os.path.join(os.path.expanduser("~"), "Documents")
    if not os.path.isdir(documentos):
        documentos = os.path.expanduser("~")
    return os.path.join(documentos, "Guias de Pregação")


def abrir_no_sistema(caminho: str):
    if sys.platform == "win32":
        os.startfile(caminho)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", caminho], check=False)
    else:
        subprocess.run(["xdg-open", caminho], check=False)


def encurtar(caminho: str, limite: int = 52) -> str:
    """Mostra o fim do caminho, que é a parte que interessa (o nome do arquivo)."""
    if len(caminho) <= limite:
        return caminho
    return "..." + caminho[-(limite - 3):]


class Aplicativo(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Guia de Pregação")
        self.geometry("780x760")
        self.minsize(720, 700)
        self.configure(bg=tema.FUNDO)

        self.p = tema.aplicar_estilos(self)

        self.caminho_audio = tk.StringVar()
        self.rotulo_audio = tk.StringVar(value="Nenhum arquivo escolhido")
        self.pregador = tk.StringVar()
        self.hoje = date.today()
        self.dia = tk.StringVar(value=str(self.hoje.day))
        self.mes = tk.StringVar(value=MESES[self.hoje.month - 1])
        self.ano = tk.StringVar(value=str(self.hoje.year))
        self.status = tk.StringVar(value="Comece escolhendo o áudio da pregação.")

        self.fila = queue.Queue()
        self.trabalhando = False
        self.transcricao = ""

        self._montar_interface()
        self.after(100, self._processar_fila)
        self.after(300, self._checar_ollama_em_segundo_plano)

    # ------------------------------------------------------------ construção

    def _montar_interface(self):
        self._montar_cabecalho()

        # rodapé antes do corpo: o corpo usa expand=True e, se vier primeiro,
        # não sobra espaço nenhum pro rodapé
        self.rodape = tk.Frame(self, bg=tema.FUNDO, height=34)
        self.rodape.pack(fill="x", side="bottom")
        self.rodape.pack_propagate(False)
        tk.Label(
            self.rodape, text=f"Os PDFs ficam em  {pasta_de_saida()}",
            bg=tema.FUNDO, fg=tema.TEXTO_FRACO, font=(tema.FONTE, 8),
        ).pack(side="left", padx=28)

        corpo = tk.Frame(self, bg=tema.FUNDO, padx=28, pady=20)
        corpo.pack(fill="both", expand=True)

        self.aviso = tk.Frame(corpo, bg=tema.AVISO_FUNDO,
                              highlightbackground=tema.AVISO_BORDA,
                              highlightthickness=1)
        interno_aviso = tk.Frame(self.aviso, bg=tema.AVISO_FUNDO, padx=14, pady=11)
        interno_aviso.pack(fill="x")
        self.aviso_texto = tk.Label(
            interno_aviso, bg=tema.AVISO_FUNDO, fg=tema.AVISO_TEXTO, justify="left",
            font=(tema.FONTE, 9), wraplength=520, text="",
        )
        self.aviso_texto.pack(side="left", anchor="w")
        self.botao_preparar = tema.BotaoPrincipal(
            interno_aviso, "Preparar agora", self._abrir_preparo,
            cor=self.p["principal"])
        self.botao_preparar.configure(font=(tema.FONTE, 9, "bold"), padx=14, pady=8)
        self.botao_preparar.pack(side="right", padx=(12, 0))

        self.cartao = tk.Frame(corpo, bg=tema.CARTAO,
                               highlightbackground=tema.BORDA, highlightthickness=1)
        self.cartao.pack(fill="x")
        interno = tk.Frame(self.cartao, bg=tema.CARTAO, padx=24, pady=22)
        interno.pack(fill="x")

        self.ancora_topo = interno  # referência pro aviso se posicionar antes

        # ---- passo 1: áudio
        self._titulo_passo(interno, "1", "Áudio da pregação")
        linha = tk.Frame(interno, bg=tema.CARTAO)
        linha.pack(fill="x", pady=(0, 20))
        self.caixa_audio = tk.Frame(linha, bg="#FBFAF9",
                                    highlightbackground=tema.BORDA,
                                    highlightthickness=1)
        self.caixa_audio.pack(side="left", fill="x", expand=True)
        tk.Label(self.caixa_audio, textvariable=self.rotulo_audio, bg="#FBFAF9",
                 fg=tema.TEXTO_FRACO, font=(tema.FONTE, 9), anchor="w",
                 padx=12, pady=9).pack(fill="x")
        ttk.Button(linha, text="Escolher arquivo", style="Secundario.TButton",
                   command=self._escolher_audio).pack(side="left", padx=(10, 0))

        # ---- passo 2: pregador
        self._titulo_passo(interno, "2", "Quem pregou")
        ttk.Entry(interno, textvariable=self.pregador, style="Campo.TEntry",
                  font=(tema.FONTE, 10)).pack(fill="x", pady=(0, 20))

        # ---- passo 3: data
        self._titulo_passo(interno, "3", "Data da pregação")
        linha_data = tk.Frame(interno, bg=tema.CARTAO)
        linha_data.pack(anchor="w", pady=(0, 4))
        ttk.Spinbox(linha_data, from_=1, to=31, width=4, textvariable=self.dia,
                    style="Campo.TSpinbox", font=(tema.FONTE, 10)).pack(side="left")
        ttk.Combobox(linha_data, values=list(MESES), textvariable=self.mes,
                     width=13, state="readonly", style="Campo.TCombobox",
                     font=(tema.FONTE, 10)).pack(side="left", padx=8)
        ttk.Spinbox(linha_data, from_=2020, to=2100, width=6, textvariable=self.ano,
                    style="Campo.TSpinbox", font=(tema.FONTE, 10)).pack(side="left")

        # ---- ação
        self.botao = tema.BotaoPrincipal(corpo, "Gerar o guia em PDF",
                                         self._iniciar, cor=self.p["principal"])
        self.botao.pack(fill="x", pady=(20, 0))

        self.barra = ttk.Progressbar(corpo, mode="determinate", maximum=100,
                                     style="Barra.Horizontal.TProgressbar")
        self.barra.pack(fill="x", pady=(16, 8))

        tk.Label(corpo, textvariable=self.status, bg=tema.FUNDO, fg=tema.TEXTO_FRACO,
                 font=(tema.FONTE, 9), wraplength=700, justify="left",
                 ).pack(anchor="w")

        self.area_resultado = tk.Frame(corpo, bg=tema.FUNDO)
        self.area_resultado.pack(fill="x", pady=(16, 0))

    def _titulo_passo(self, mestre, numero, texto):
        linha = tk.Frame(mestre, bg=tema.CARTAO)
        linha.pack(fill="x", pady=(0, 8))
        tk.Label(linha, text=numero, bg=self.p["principal_claro"],
                 fg=self.p["principal"], font=(tema.FONTE, 9, "bold"),
                 width=3, pady=2).pack(side="left")
        tk.Label(linha, text=texto, bg=tema.CARTAO, fg=tema.TEXTO,
                 font=(tema.FONTE, 10, "bold")).pack(side="left", padx=9)

    def _montar_cabecalho(self):
        self.cabecalho = tk.Frame(self, bg=self.p["principal"], height=96)
        self.cabecalho.pack(fill="x")
        self.cabecalho.pack_propagate(False)

        textos = tk.Frame(self.cabecalho, bg=self.p["principal"])
        textos.pack(side="left", anchor="w", padx=28, pady=(20, 0))
        self.titulo = tk.Label(
            textos, text="Guia de Pregação", bg=self.p["principal"],
            fg=self.p["sobre_principal"], font=(tema.FONTE, 21, "bold"),
        )
        self.titulo.pack(anchor="w")
        self.subtitulo = tk.Label(
            textos, text=config.NOME_IGREJA, bg=self.p["principal"],
            fg=self.p["sobre_principal"], font=(tema.FONTE, 10),
        )
        self.subtitulo.pack(anchor="w", pady=(2, 0))

        self.engrenagem = tk.Label(
            self.cabecalho, text="⚙  Configurações", bg=self.p["principal"],
            fg=self.p["sobre_principal"], font=(tema.FONTE, 9), cursor="hand2",
            padx=10, pady=5,
        )
        self.engrenagem.pack(side="right", anchor="ne", padx=22, pady=18)
        self.engrenagem.bind("<Button-1>", lambda _: self._abrir_configuracoes())
        self.engrenagem.bind(
            "<Enter>", lambda _: self.engrenagem.configure(
                bg=tema.escurecer(self.p["principal"], 0.18)))
        self.engrenagem.bind(
            "<Leave>", lambda _: self.engrenagem.configure(bg=self.p["principal"]))

    # ----------------------------------------------------------------- ollama

    def _checar_ollama_em_segundo_plano(self):
        """
        Vê se falta alguma peça. Se o Ollama estiver instalado mas parado, tenta
        ligar sozinho antes de incomodar a pessoa — é o caso mais comum e não
        exige download nenhum.
        """
        def checar():
            import instalador

            if instalador.caminho_ollama() and not instalador.servidor_no_ar():
                instalador.iniciar_servidor(lambda *_: None)

            self.fila.put(("diagnostico", instalador.diagnostico()))

        threading.Thread(target=checar, daemon=True).start()

    def _abrir_preparo(self):
        import tela_preparo

        def terminou(sucesso):
            if sucesso:
                self.aviso.pack_forget()
            self._checar_ollama_em_segundo_plano()

        tela_preparo.TelaPreparo(self, ao_terminar=terminou)

    # ------------------------------------------------------------------ ações

    def _escolher_audio(self):
        caminho = filedialog.askopenfilename(
            title="Escolha o áudio da pregação", filetypes=FORMATOS_AUDIO
        )
        if caminho:
            self.caminho_audio.set(caminho)
            self.rotulo_audio.set(encurtar(caminho))
            self.caixa_audio.configure(highlightbackground=self.p["principal"])
            self.status.set("Áudio escolhido. Preencha o pregador e clique em gerar.")

    def _data_escolhida(self):
        try:
            return date(int(self.ano.get()), MESES.index(self.mes.get()) + 1,
                        int(self.dia.get()))
        except (ValueError, IndexError):
            return None

    def _iniciar(self):
        if self.trabalhando:
            return

        audio = self.caminho_audio.get().strip()
        if not audio or not os.path.isfile(audio):
            messagebox.showerror("Falta o áudio", "Escolha um arquivo de áudio válido.")
            return
        if not self.pregador.get().strip():
            messagebox.showerror("Falta o pregador", "Preencha quem pregou.")
            return
        data = self._data_escolhida()
        if data is None:
            messagebox.showerror("Data inválida", "Confira o dia, o mês e o ano.")
            return

        for w in self.area_resultado.winfo_children():
            w.destroy()

        self.trabalhando = True
        self.botao.habilitar(False, "Gerando...")
        self.barra["value"] = 0

        threading.Thread(
            target=self._pipeline,
            args=(audio, self.pregador.get().strip(), data),
            daemon=True,
        ).start()

    # --------------------------------------------------- trabalho pesado

    def _pipeline(self, audio, pregador, data):
        """Roda numa thread separada. Só fala com a interface pela fila."""
        try:
            # imports aqui dentro: carregar o faster-whisper demora alguns
            # segundos e travaria a abertura da janela se fosse no topo
            from transcrever import transcrever_audio
            from gerar_conteudo import gerar_guia
            from gerar_pdf import gerar_pdf

            self.fila.put(("status", (2, "Carregando o modelo de transcrição... "
                                         "(na primeira vez ele baixa, pode demorar)")))

            def progresso(p):
                self.fila.put(("status", (2 + p * 60,
                                          f"Transcrevendo o áudio... {int(p * 100)}%")))

            texto = transcrever_audio(audio, progresso_callback=progresso)
            self.fila.put(("transcricao", texto))

            # A transcrição levou minutos; nesse meio tempo o motor de IA pode
            # ter sido desligado, ou nunca ter subido. Garante antes de chamar,
            # senão a pessoa perde todo o trabalho da transcrição por causa
            # de um serviço parado.
            import instalador
            if not instalador.servidor_no_ar():
                self.fila.put(("status", (66, "Ligando o motor de IA...")))
                instalador.iniciar_servidor(lambda *_: None)

            # a IA ocupa a faixa de 68% a 90% da barra
            def progresso_ia(fracao, descricao):
                self.fila.put(("status", (68 + fracao * 22, descricao)))

            dados = gerar_guia(texto, pregador=pregador, data=formatar_data(data),
                               progresso=progresso_ia)

            self.fila.put(("status", (90, "Montando o PDF...")))
            pasta = pasta_de_saida()
            os.makedirs(pasta, exist_ok=True)
            nome = f"{data.isoformat()}-{pregador.replace(' ', '_')}.pdf"
            caminho = gerar_pdf(dados, os.path.join(pasta, nome))

            self.fila.put(("pronto", caminho))

        except Exception as e:
            self.fila.put(("erro", (e, traceback.format_exc())))

    # ------------------------------------------------- ponte thread → interface

    def _processar_fila(self):
        try:
            while True:
                tipo, carga = self.fila.get_nowait()

                if tipo == "status":
                    valor, texto = carga
                    self.barra["value"] = valor
                    self.status.set(texto)

                elif tipo == "transcricao":
                    self.transcricao = carga

                elif tipo == "diagnostico":
                    self._mostrar_diagnostico(carga)

                elif tipo == "pronto":
                    self._concluir(carga)

                elif tipo == "erro":
                    self._falhar(*carga)

        except queue.Empty:
            pass
        self.after(100, self._processar_fila)

    def _mostrar_diagnostico(self, d):
        """Uma faixa só, com o que falta e o botão que resolve."""
        if d["servidor_no_ar"] and d["modelo_ia"] and d["modelo_transcricao"]:
            self.aviso.pack_forget()
            return

        faltando = []
        if not d["ollama_instalado"]:
            faltando.append("o motor de IA")
        elif not d["servidor_no_ar"]:
            faltando.append("ligar o motor de IA")
        if not d["modelo_ia"]:
            faltando.append(f"o modelo {config.OLLAMA_MODEL}")
        if not d["modelo_transcricao"]:
            faltando.append("o modelo de transcrição")

        gb = __import__("instalador").falta_baixar_gb(d)
        texto = ("Falta preparar " + ", ".join(faltando) + ". "
                 f"São cerca de {gb:.1f} GB, baixados uma vez só — "
                 "o programa cuida disso pra você.")
        self.aviso_texto.config(text=texto)
        self.aviso.pack(fill="x", pady=(0, 16), before=self.cartao)

    def _concluir(self, caminho):
        self.trabalhando = False
        self.barra["value"] = 100
        self.botao.habilitar(True, "Gerar o guia em PDF")
        self.status.set("Pronto!")

        painel = tk.Frame(self.area_resultado, bg=tema.CARTAO,
                          highlightbackground=tema.BORDA, highlightthickness=1)
        painel.pack(fill="x")
        dentro = tk.Frame(painel, bg=tema.CARTAO, padx=18, pady=14)
        dentro.pack(fill="x")

        tk.Label(dentro, text="✓  Guia gerado", bg=tema.CARTAO, fg=tema.SUCESSO,
                 font=(tema.FONTE, 10, "bold")).pack(anchor="w")
        tk.Label(dentro, text=encurtar(caminho, 70), bg=tema.CARTAO,
                 fg=tema.TEXTO_FRACO, font=(tema.FONTE, 8)).pack(anchor="w",
                                                                 pady=(1, 10))

        botoes = tk.Frame(dentro, bg=tema.CARTAO)
        botoes.pack(anchor="w")
        ttk.Button(botoes, text="Abrir o PDF", style="Secundario.TButton",
                   command=lambda: abrir_no_sistema(caminho)).pack(side="left")
        ttk.Button(botoes, text="Abrir a pasta", style="Secundario.TButton",
                   command=lambda: abrir_no_sistema(os.path.dirname(caminho))
                   ).pack(side="left", padx=8)
        ttk.Button(botoes, text="Ver transcrição", style="Secundario.TButton",
                   command=self._mostrar_transcricao).pack(side="left")

    def _registrar_erro(self, detalhe: str) -> str:
        """
        Grava o traceback num arquivo. Empacotado com --windowed não existe
        stderr, então sem isto o erro real morre com a janela e não há como
        alguém descobrir o que aconteceu.
        """
        caminho = os.path.join(os.path.dirname(config.caminho_ajustes()), "erros.log")
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 70}\n{datetime.now():%d/%m/%Y %H:%M:%S}\n{detalhe}")
        except OSError:
            return ""
        return caminho

    def _falhar(self, erro, detalhe):
        self.trabalhando = False
        self.botao.habilitar(True, "Gerar o guia em PDF")
        self.barra["value"] = 0

        registro = self._registrar_erro(detalhe)

        # Checa o TIPO da exceção, não o texto dela. Antes isto procurava
        # "connect" na mensagem e classificava como problema de conexão
        # qualquer erro que por acaso tivesse essa palavra — mostrando à pessoa
        # uma causa errada e escondendo a de verdade.
        import requests.exceptions as re_exc
        sem_conexao = isinstance(erro, (re_exc.ConnectionError, ConnectionError))
        demorou = isinstance(erro, (re_exc.Timeout, TimeoutError))

        if sem_conexao:
            amigavel = ("O motor de IA não respondeu.\n\n"
                        "Feche e abra o programa — ele liga o motor sozinho. "
                        "Se continuar, use o botão Preparar agora na tela inicial.")
        elif demorou:
            amigavel = ("A IA demorou mais do que o limite e o processo foi "
                        "interrompido.\n\nIsso acontece em computador mais lento com "
                        "pregação longa. A transcrição não se perdeu — ela está no "
                        "botão Ver transcrição.")
        else:
            amigavel = f"Deu erro no processo:\n\n{type(erro).__name__}: {erro}"

        if registro:
            amigavel += f"\n\nDetalhes técnicos foram salvos em:\n{registro}"

        self.status.set("Não deu certo — veja a mensagem.")
        messagebox.showerror("Erro", amigavel)
        if sys.stderr is not None:
            print(detalhe, file=sys.stderr)

    # ---------------------------------------------------------- configurações

    def _abrir_configuracoes(self):
        campos = [
            ("NOME_IGREJA", "Nome da igreja"),
            ("LEMA", "Lema (aparece no rodapé do PDF)"),
            ("COR_PRIMARIA", "Cor principal — cabeçalho e títulos (hex)"),
            ("COR_DESTAQUE", "Cor de destaque — filetes e números (hex)"),
            ("COR_SECUNDARIA", "Cor de fundo das caixas (hex)"),
            ("INSTAGRAM", "Instagram"),
            ("YOUTUBE", "YouTube (deixe vazio para não aparecer)"),
            ("OLLAMA_MODEL", "Modelo da IA (ollama)"),
            ("WHISPER_MODEL", "Transcrição (small / medium / large-v3)"),
        ]

        janela = tk.Toplevel(self)
        janela.title("Configurações")
        janela.configure(bg=tema.FUNDO)
        janela.transient(self)
        janela.grab_set()
        janela.resizable(False, False)

        faixa = tk.Frame(janela, bg=self.p["principal"], height=54)
        faixa.pack(fill="x")
        faixa.pack_propagate(False)
        tk.Label(faixa, text="Identidade da igreja", bg=self.p["principal"],
                 fg=self.p["sobre_principal"], font=(tema.FONTE, 12, "bold"),
                 ).pack(anchor="w", padx=22, pady=14)

        quadro = tk.Frame(janela, bg=tema.FUNDO, padx=22, pady=18)
        quadro.pack(fill="both", expand=True)

        variaveis = {}
        for chave, rotulo in campos:
            tk.Label(quadro, text=rotulo, bg=tema.FUNDO, fg=tema.TEXTO,
                     font=(tema.FONTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar(value=str(getattr(config, chave, "")))
            ttk.Entry(quadro, textvariable=var, width=46, style="Campo.TEntry",
                      font=(tema.FONTE, 10)).pack(fill="x", pady=(3, 11))
            variaveis[chave] = var

        tk.Label(quadro, bg=tema.FUNDO, fg=tema.TEXTO_FRACO, font=(tema.FONTE, 8),
                 justify="left", wraplength=400,
                 text=f"Salvo em {config.caminho_ajustes()}\n"
                      "Vale para o PDF e para esta janela.",
                 ).pack(anchor="w", pady=(2, 14))

        def salvar():
            config.salvar_ajustes({c: v.get().strip() for c, v in variaveis.items()})
            self._aplicar_identidade()
            janela.destroy()
            messagebox.showinfo("Configurações", "Salvo. Já vale para o próximo PDF.")

        botoes = tk.Frame(quadro, bg=tema.FUNDO)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Salvar", style="Secundario.TButton",
                   command=salvar).pack(side="right")
        ttk.Button(botoes, text="Cancelar", style="Secundario.TButton",
                   command=janela.destroy).pack(side="right", padx=8)

    def _aplicar_identidade(self):
        """Repinta a interface depois que as configurações mudam."""
        self.p = tema.aplicar_estilos(self)
        principal, sobre = self.p["principal"], self.p["sobre_principal"]

        self.cabecalho.configure(bg=principal)
        self.titulo.master.configure(bg=principal)
        self.titulo.configure(bg=principal, fg=sobre)
        self.subtitulo.configure(bg=principal, fg=sobre, text=config.NOME_IGREJA)
        self.engrenagem.configure(bg=principal, fg=sobre)
        self.botao.definir_cor(principal)
        self.botao_preparar.definir_cor(principal)

    def _mostrar_transcricao(self):
        janela = tk.Toplevel(self)
        janela.title("Transcrição bruta")
        janela.geometry("720x520")
        janela.configure(bg=tema.FUNDO)
        caixa = tk.Text(janela, wrap="word", font=(tema.FONTE, 10), padx=16,
                        pady=14, bg=tema.CARTAO, fg=tema.TEXTO, relief="flat",
                        borderwidth=0)
        barra = ttk.Scrollbar(janela, command=caixa.yview)
        caixa.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        caixa.pack(fill="both", expand=True, padx=16, pady=16)
        caixa.insert("1.0", self.transcricao or "(vazio)")
        caixa.config(state="disabled")


if __name__ == "__main__":
    Aplicativo().mainloop()
