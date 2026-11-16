import sys
from pathlib import Path
from processador_media import process_meeting_media
from processador_texto import process_meeting_text  # Confirme se a função no processador_texto.py tem este nome

EXTENSOES_TEXTO = {".txt", ".md"}
EXTENSOES_MEDIA = {".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mpeg", ".mov"}


def run_smartmeeting(file_path: str):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro não encontrado em: {file_path}")

    extensao = path.suffix.lower()

    if extensao in EXTENSOES_TEXTO:
        print("-> Modo Texto detetado. A encaminhar para processador_texto...")
        conteudo = path.read_text(encoding="utf-8")
        return process_meeting_text(conteudo)

    if extensao in EXTENSOES_MEDIA:
        print("-> Modo Multimédia detetado. A encaminhar para processador_media...")
        return process_meeting_media(str(path))

    raise ValueError(
        f"Formato '{extensao}' não suportado. "
        f"Use texto ({', '.join(EXTENSOES_TEXTO)}) ou multimédia ({', '.join(EXTENSOES_MEDIA)})."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: py backend.py <caminho_do_ficheiro>")
        print("Exemplo áudio: py backend.py reuniao.mp3")
        print("Exemplo texto: py backend.py transcricao.txt")
        sys.exit(1)

    target_file = sys.argv[1]
    print(f"SmartMeeting AI Engine iniciado. Ficheiro: {target_file}")
    run_smartmeeting(target_file)