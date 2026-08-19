"""
Transcreve o áudio da pregação para texto usando faster-whisper.
100% gratuito e roda offline (não manda áudio pra nenhuma API paga).
"""

from faster_whisper import WhisperModel
import config

_modelo = None  # carregado uma única vez e reaproveitado


def carregar_modelo():
    global _modelo
    if _modelo is None:
        print(f"Carregando modelo Whisper '{config.WHISPER_MODEL}' "
              f"(primeira vez pode demorar, ele baixa o modelo)...")
        _modelo = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _modelo


def transcrever_audio(caminho_audio: str, progresso_callback=None) -> str:
    """
    Recebe o caminho de um arquivo de áudio (mp3, wav, m4a, etc.)
    e devolve o texto transcrito em português.
    """
    modelo = carregar_modelo()

    segmentos, info = modelo.transcribe(
        caminho_audio,
        language="pt",
        beam_size=5,
        vad_filter=True,  # remove silêncios longos, acelera e melhora a qualidade
    )

    texto_completo = []
    duracao_total = info.duration

    for segmento in segmentos:
        texto_completo.append(segmento.text.strip())
        if progresso_callback and duracao_total:
            progresso_callback(min(segmento.end / duracao_total, 1.0))

    return " ".join(texto_completo)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python transcrever.py caminho/do/audio.mp3")
        sys.exit(1)

    texto = transcrever_audio(sys.argv[1])
    print("\n--- TRANSCRIÇÃO ---\n")
    print(texto)
