# Gerador de Guia da Pregação

Pega o áudio da pregação, transcreve, organiza com IA no formato de guia de
estudo em família e gera um PDF com a identidade visual da igreja.

**Roda 100% no seu computador.** Nada de áudio ou texto sai da máquina, e não
há custo por uso — nem API paga, nem assinatura, nem limite.

## Como funciona

```
Áudio (celular / gravador)
        │
        ▼
  transcrever.py      → faster-whisper transforma fala em texto
        │
        ▼
  gerar_conteudo.py   → Ollama organiza no formato do guia (JSON)
        │
        ▼
  gerar_pdf.py        → aplica o template e exporta
        │  └── motor_pdf.py → Edge (padrão) ou weasyprint
        ▼
  app_desktop.py      → a janela que a pessoa usa
```

## Instalação

### Usando o executável
Abra o programa. Na primeira vez ele mostra a tela **"Falta preparar o
programa"**, com a lista do que falta e o tamanho do download. Um clique em
*Baixar e preparar* e ele resolve tudo sozinho: instala o Ollama, liga o
serviço e baixa os dois modelos, mostrando o progresso.

Não precisa abrir Prompt de Comando nenhum.

> O programa **escolhe os modelos pela memória da sua máquina** — abaixo de
> 15 GB de RAM ele usa os leves, acima disso os mais precisos. Ver a tabela em
> [Escolhendo os modelos](#escolhendo-os-modelos-conforme-a-máquina).

### Rodando a partir do código

#### 1. Python 3.10 ou mais novo
Baixe em [python.org](https://www.python.org/downloads/). Depois:

```bash
cd pregacao-pdf
pip install -r requirements.txt
```

> **Se der `No module named pip`:** alguns instaladores do Python no Windows vêm
> sem ele. Conserta com `python -m ensurepip --upgrade`.

#### 2. Ollama
A tela de preparo do aplicativo cuida disso. Se preferir fazer à mão, baixe em
[ollama.com/download](https://ollama.com/download) e rode:

```bash
ollama pull llama3.2
```

Pra ver o que está pronto e o que falta, sem abrir a interface:

```bash
python instalador.py
```

#### 3. Configurar a identidade da igreja
Abra o aplicativo e clique em **⚙ Configurações**. Dá pra ajustar nome, lema,
as três cores, Instagram e YouTube sem mexer em código — fica salvo em
`%APPDATA%\GuiaPregacao\configuracao.json`.

Os valores padrão vivem em `config.py`, e o JSON sobrescreve o que estiver lá.

## Como usar

```bash
python app_desktop.py
```

Escolha o áudio, preencha quem pregou e a data, clique em **Gerar o guia em
PDF**. Os arquivos saem em `Documentos\Guias de Pregação`.

Uma pregação de ~50 min leva de 5 a 15 minutos em máquina sem placa de vídeo.
A janela continua respondendo — o trabalho roda em outra thread.

## Escolhendo os modelos conforme a máquina

Os dois modelos rodam **ao mesmo tempo** no seu computador, então some a RAM
dos dois:

| RAM da máquina | `OLLAMA_MODEL` | `WHISPER_MODEL` |
|---|---|---|
| 8 GB | `llama3.2` (~2 GB) | `small` (~0,5 GB) |
| 16 GB | `llama3.1` (~5 GB) | `medium` (~2,5 GB) |
| 32 GB+ | `llama3.1` | `large-v3` (~5 GB) |

Pedir mais do que a máquina tem não dá erro — o Windows começa a usar o disco
como memória e **o computador trava**. Se isso acontecer, desça um degrau.

## Gerar o executável

```bash
pip install pyinstaller
python build_exe.py
```

Sai em `dist/Guia de Pregacao/`. Distribua a **pasta inteira** (zipada, ou com
um instalador).

### Atalho na Área de Trabalho

```bash
python criar_atalho.py
```

Põe o atalho, com ícone, na Área de Trabalho **e** no Menu Iniciar (aí ele
aparece na busca do Windows). Funciona antes do build também: nesse caso o
atalho chama o código-fonte pelo `pythonw.exe`, sem janela preta de terminal.

### Manual de instalação em PDF

```bash
python gerar_manual.py
```

Gera `pdfs/Como-instalar-o-Guia-de-Pregacao.pdf` — duas páginas, com o passo a
passo para quem vai instalar em outro computador. Sai com as cores da igreja,
igual ao guia da pregação. O link de download fica em `URL_DOWNLOAD`, no topo
do script.

### Trocar o ícone

```bash
python fazer_icone.py
```

O ícone é desenhado a partir de `COR_PRIMARIA` e `COR_DESTAQUE`, então
mudando as cores da igreja e rodando de novo ele acompanha. São dois desenhos:
uma Bíblia aberta com chama para 48 px ou mais, e só a chama para 16 e 32 px —
o desenho completo vira borrão nesse tamanho.

---

O Ollama e os modelos **não vão dentro do pacote** — juntos passam de 3 GB e
inchariam o download pra todo mundo, inclusive pra quem já tem. Em vez disso,
quem receber vê a tela de preparo na primeira abertura e o programa baixa o que
falta na máquina dela.

## Os dois motores de PDF

`motor_pdf.py` converte o HTML do template em PDF por dois caminhos:

- **`edge`** (padrão no Windows) — usa o Microsoft Edge em modo headless. Já
  vem no sistema, não precisa instalar nada e sobrevive ao empacotamento.
- **`weasyprint`** — o motor original. Tipografia um pouco melhor, mas no
  Windows exige o GTK instalado à parte. É o padrão no Linux e no Mac.

Pra forçar um deles: `gerar_pdf(dados, caminho, motor="weasyprint")`.

## Pegadinhas do Windows que já estão resolvidas

Ficam registradas aqui pra ninguém perder tempo de novo:

- **`cannot load library 'libgobject-2.0-0'`** — o weasyprint depende do GTK, e
  desde o Python 3.8 o `PATH` não resolve mais DLLs dependentes. `motor_pdf.py`
  chama `os.add_dll_directory()` apontando a pasta do GTK.
- **PDF com cabeçalho branco** — navegador não imprime cor de fundo por padrão.
  O template usa `print-color-adjust: exact`.
- **PDF que não aparece** — o `msedge.exe` delega pra um processo filho e sai
  com código 0 *antes* de escrever o arquivo. Por isso `motor_pdf.py` espera o
  arquivo aparecer e parar de crescer, em vez de confiar no código de saída.
- **Mês em inglês no PDF** — `strftime("%B")` depende do locale, e no Windows o
  nome é `Portuguese_Brazil` e não `pt_BR`. A lista de meses é escrita na mão.
- **Rodapé repetido em toda página** — `position: fixed` faz isso no weasyprint,
  mas no Edge ele solta o rodapé no topo da página seguinte e empurra conteúdo
  pra fora. O rodapé fecha o documento em fluxo normal.

## Testar cada parte separadamente

```bash
python transcrever.py audios/exemplo.mp3   # só a transcrição
python gerar_pdf.py                        # só o PDF, com dados de exemplo
python gerar_conteudo.py                   # só a IA (precisa do Ollama de pé)
python instalador.py                       # o que está pronto e o que falta
```

## Estrutura

```
pregacao-pdf/
├── app_desktop.py     → aplicativo desktop (tkinter)
├── tema.py            → paleta e estilos do app, derivados de COR_PRIMARIA
├── instalador.py      → detecta e baixa o que falta (Ollama, modelos)
├── tela_preparo.py    → tela de primeira execução
├── config.py          → padrões da igreja e dos modelos
├── transcrever.py     → áudio → texto
├── gerar_conteudo.py  → texto → JSON estruturado
├── gerar_pdf.py       → JSON → PDF
├── motor_pdf.py       → HTML → PDF (Edge ou weasyprint)
├── build_exe.py       → empacota o aplicativo
├── criar_atalho.py    → põe o atalho na Área de Trabalho e no Menu Iniciar
├── fazer_icone.py     → desenha o ícone a partir das cores do config
├── gerar_manual.py    → PDF com o passo a passo de instalação
├── templates/guia.html→ o desenho do PDF (pode editar o HTML/CSS)
├── audios/            → coloque os áudios aqui
└── pdfs/              → saída dos testes por linha de comando
```

## Ideias pra depois

- Campo manual de passagem bíblica, pra garantir precisão em vez de deixar a IA
  inferir do contexto
- Logo da igreja no cabeçalho do PDF (o `LOGO_PATH` já existe no config, mas o
  template ainda não usa)
- Salvar os PDFs direto numa pasta compartilhada do Drive
