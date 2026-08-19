"""
Tela de primeira execução.

Aparece quando falta alguma peça (Ollama, modelo de IA, modelo de transcrição)
e cuida do download com um clique só.

A pessoa vê o que vai ser baixado e o tamanho ANTES de qualquer coisa começar.
São alguns GB e um programa de terceiro entrando na máquina — isso se pergunta,
não se faz escondido enquanto a janela finge estar carregando.
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import config
import instalador
import tema


class TelaPreparo(tk.Toplevel):
    def __init__(self, mestre, ao_terminar=None):
        super().__init__(mestre)
        self.ao_terminar = ao_terminar
        self.p = tema.paleta()
        self.fila = queue.Queue()
        self.rodando = False
        self.cancelar = False
        self.sucesso = False

        self.title("Preparar o programa")
        self.configure(bg=tema.FUNDO)
        # tamanho fixo: deixado no automático, o tk fecha a janela menor que o
        # conteúdo e corta o texto e os botões
        self.geometry("620x640")
        self.minsize(620, 640)
        self.resizable(False, False)
        self.transient(mestre)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self.diag = instalador.diagnostico()
        self._montar()
        self.after(100, self._processar_fila)

    # ---------------------------------------------------------------- layout

    def _montar(self):
        faixa = tk.Frame(self, bg=self.p["principal"], height=76)
        faixa.pack(fill="x")
        faixa.pack_propagate(False)
        tk.Label(faixa, text="Falta preparar o programa", bg=self.p["principal"],
                 fg=self.p["sobre_principal"], font=(tema.FONTE, 15, "bold"),
                 ).pack(anchor="w", padx=26, pady=(16, 0))
        tk.Label(faixa, text="É uma vez só. Depois disso abre direto.",
                 bg=self.p["principal"], fg=self.p["sobre_principal"],
                 font=(tema.FONTE, 9)).pack(anchor="w", padx=26)

        corpo = tk.Frame(self, bg=tema.FUNDO, padx=26, pady=20)
        corpo.pack(fill="both", expand=True)

        tk.Label(corpo, bg=tema.FUNDO, fg=tema.TEXTO, justify="left",
                 font=(tema.FONTE, 10), wraplength=540,
                 text="Para funcionar sem internet e sem custo, o programa precisa "
                      "baixar os motores que rodam na sua máquina:",
                 ).pack(anchor="w", pady=(0, 14))

        lista = tk.Frame(corpo, bg=tema.CARTAO, highlightbackground=tema.BORDA,
                         highlightthickness=1)
        lista.pack(fill="x")
        dentro = tk.Frame(lista, bg=tema.CARTAO, padx=18, pady=14)
        dentro.pack(fill="x")

        for pronto, titulo, detalhe in self._itens():
            linha = tk.Frame(dentro, bg=tema.CARTAO)
            linha.pack(fill="x", pady=3)
            tk.Label(linha, text="✓" if pronto else "↓", bg=tema.CARTAO,
                     fg=tema.SUCESSO if pronto else self.p["principal"],
                     font=(tema.FONTE, 11, "bold"), width=2).pack(side="left")
            tk.Label(linha, text=titulo, bg=tema.CARTAO,
                     fg=tema.TEXTO_FRACO if pronto else tema.TEXTO,
                     font=(tema.FONTE, 9, "normal" if pronto else "bold"),
                     ).pack(side="left")
            tk.Label(linha, text=detalhe, bg=tema.CARTAO, fg=tema.TEXTO_FRACO,
                     font=(tema.FONTE, 8)).pack(side="right")

        ram = self.diag["ram_gb"]
        rec = instalador.recomendar_modelos()
        tk.Label(corpo, bg=tema.FUNDO, fg=tema.TEXTO_FRACO, justify="left",
                 font=(tema.FONTE, 8), wraplength=540,
                 text=f"Seu computador tem {ram:.1f} GB de memória, então foram "
                      f"escolhidos os modelos {rec['ollama']} e {rec['whisper']}, "
                      f"que cabem com folga. Espaço livre em disco: "
                      f"{self.diag['espaco_livre_gb']:.0f} GB.",
                 ).pack(anchor="w", pady=(12, 0))

        self.area_progresso = tk.Frame(corpo, bg=tema.FUNDO)
        self.area_progresso.pack(fill="x", pady=(16, 0))
        self.rotulo_passo = tk.Label(
            self.area_progresso, bg=tema.FUNDO, fg=tema.TEXTO, anchor="w",
            font=(tema.FONTE, 9, "bold"), text="")
        self.rotulo_passo.pack(fill="x")
        self.barra = ttk.Progressbar(self.area_progresso, mode="determinate",
                                     maximum=100,
                                     style="Barra.Horizontal.TProgressbar")
        self.barra.pack(fill="x", pady=(6, 4))
        self.rotulo_detalhe = tk.Label(
            self.area_progresso, bg=tema.FUNDO, fg=tema.TEXTO_FRACO, anchor="w",
            font=(tema.FONTE, 8), text="")
        self.rotulo_detalhe.pack(fill="x")

        rodape = tk.Frame(corpo, bg=tema.FUNDO)
        rodape.pack(fill="x", pady=(18, 0))
        self.botao_depois = ttk.Button(rodape, text="Agora não",
                                       style="Secundario.TButton",
                                       command=self._fechar)
        self.botao_depois.pack(side="left")

        gb = instalador.falta_baixar_gb(self.diag)
        self.botao_preparar = tema.BotaoPrincipal(
            rodape, f"Baixar e preparar  ({gb:.1f} GB)", self._comecar,
            cor=self.p["principal"])
        self.botao_preparar.configure(font=(tema.FONTE, 10, "bold"), padx=18, pady=9)
        self.botao_preparar.pack(side="right")

    def _itens(self):
        d = self.diag
        return [
            (d["ollama_instalado"], "Motor de IA (Ollama)", "~1 GB"),
            (d["modelo_ia"], f"Modelo {config.OLLAMA_MODEL}",
             f"~{instalador.CUSTO_OLLAMA.get(config.OLLAMA_MODEL.split(':')[0], 2.5):.0f} GB"),
            (d["modelo_transcricao"], f"Transcrição ({config.WHISPER_MODEL})",
             f"~{instalador.CUSTO_WHISPER.get(config.WHISPER_MODEL, 0.6):.1f} GB"),
        ]

    # ----------------------------------------------------------------- ações

    def _comecar(self):
        if self.rodando:
            return
        self.rodando = True
        self.botao_preparar.habilitar(False, "Baixando...")
        self.botao_depois.configure(text="Cancelar")

        threading.Thread(target=self._trabalhar, daemon=True).start()

    def _trabalhar(self):
        try:
            instalador.preparar(
                passo=lambda i, t, titulo: self.fila.put(("passo", (i, t, titulo))),
                aviso=lambda f, d: self.fila.put(("aviso", (f, d))),
                cancelou=lambda: self.cancelar,
            )
            self.fila.put(("pronto", None))
        except instalador.Cancelado:
            self.fila.put(("cancelado", None))
        except Exception as e:
            self.fila.put(("erro", e))

    def _processar_fila(self):
        try:
            while True:
                tipo, carga = self.fila.get_nowait()

                if tipo == "passo":
                    i, total, titulo = carga
                    self.rotulo_passo.configure(text=f"Passo {i} de {total}: {titulo}")
                    self.barra["value"] = 0

                elif tipo == "aviso":
                    fracao, detalhe = carga
                    if fracao is None:
                        self.barra.configure(mode="indeterminate")
                        self.barra.start(12)
                    else:
                        self.barra.stop()
                        self.barra.configure(mode="determinate")
                        self.barra["value"] = fracao * 100
                    self.rotulo_detalhe.configure(text=detalhe)

                elif tipo == "pronto":
                    self.barra.stop()
                    self.barra.configure(mode="determinate")
                    self.barra["value"] = 100
                    self.sucesso = True
                    self.rodando = False
                    messagebox.showinfo(
                        "Tudo pronto",
                        "O programa está preparado. Agora é só escolher o áudio "
                        "da pregação.", parent=self)
                    self._encerrar()

                elif tipo == "cancelado":
                    self.rodando = False
                    self._encerrar()

                elif tipo == "erro":
                    self.barra.stop()
                    self.rodando = False
                    self.botao_preparar.habilitar(True, "Tentar de novo")
                    self.botao_depois.configure(text="Agora não")
                    self.rotulo_passo.configure(text="Não deu certo")
                    self.rotulo_detalhe.configure(text="")
                    messagebox.showerror("Erro no preparo", str(carga), parent=self)

        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._processar_fila)

    def _fechar(self):
        if self.rodando:
            if not messagebox.askyesno(
                    "Cancelar", "O download está em andamento. Cancelar mesmo?",
                    parent=self):
                return
            self.cancelar = True
            return
        self._encerrar()

    def _encerrar(self):
        if self.ao_terminar:
            self.ao_terminar(self.sucesso)
        self.grab_release()
        self.destroy()
