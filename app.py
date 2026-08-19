"""
Interface simples para gerar o Guia de Pregação em PDF.
Rode com:  streamlit run app.py
Depois é só abrir o link que aparece no navegador (funciona na rede local
também, então dá pra qualquer um na igreja acessar pelo celular).
"""

import os
import tempfile
from datetime import date

import streamlit as st

import config
from transcrever import transcrever_audio
from gerar_conteudo import gerar_guia
from gerar_pdf import gerar_pdf

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def formatar_data(d: date) -> str:
    """
    "19 de agosto de 2026" — feito na mão de propósito: strftime("%B") depende
    do locale do sistema e no Windows sai em inglês ("August").
    """
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


st.set_page_config(page_title="Guia de Pregação", page_icon="📖")

st.title("📖 Gerador de Guia da Pregação")
st.caption(f"{config.NOME_IGREJA} — transcrição e formatação automática por IA (100% local e gratuito)")

with st.form("dados_pregacao"):
    audio = st.file_uploader(
        "Áudio da pregação (mp3, wav, m4a...)", type=["mp3", "wav", "m4a", "ogg", "aac"]
    )
    col1, col2 = st.columns(2)
    with col1:
        pregador = st.text_input("Pregador", placeholder="Ex: Pr. João Silva")
    with col2:
        data_pregacao = st.date_input("Data", value=date.today())

    enviar = st.form_submit_button("Gerar PDF", type="primary")

if enviar:
    if not audio:
        st.error("Envie o arquivo de áudio primeiro.")
        st.stop()
    if not pregador:
        st.error("Preencha o nome do pregador.")
        st.stop()

    # salva o áudio enviado num arquivo temporário
    sufixo = os.path.splitext(audio.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
        tmp.write(audio.read())
        caminho_audio = tmp.name

    barra = st.progress(0.0, text="Transcrevendo o áudio... (pode levar alguns minutos)")

    try:
        texto = transcrever_audio(
            caminho_audio,
            progresso_callback=lambda p: barra.progress(p * 0.6, text=f"Transcrevendo... {int(p * 100)}%")
        )

        barra.progress(0.65, text="Organizando o conteúdo com a IA...")
        data_formatada = formatar_data(data_pregacao)
        dados = gerar_guia(texto, pregador=pregador, data=data_formatada)

        barra.progress(0.9, text="Montando o PDF...")
        nome_arquivo = f"{data_pregacao.isoformat()}-{pregador.replace(' ', '_')}.pdf"
        caminho_pdf = os.path.join(config.PASTA_PDFS, nome_arquivo)
        gerar_pdf(dados, caminho_pdf)

        barra.progress(1.0, text="Pronto!")

        st.success("Guia gerado com sucesso!")
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                "⬇️ Baixar PDF", data=f, file_name=nome_arquivo, mime="application/pdf"
            )

        with st.expander("Ver transcrição bruta (caso queira conferir)"):
            st.text(texto)

    except Exception as e:
        st.error(f"Deu erro no processo: {e}")
    finally:
        os.remove(caminho_audio)
