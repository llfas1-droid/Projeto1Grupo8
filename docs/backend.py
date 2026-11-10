import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "A variável GEMINI_API_KEY não foi encontrada no ficheiro .env. "
        "Por favor, configure GEMINI_API_KEY='a_sua_chave' no .env."
    )

# 2. Inicializa o cliente oficial da Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)


def wait_for_file_processing(file_ref):
    """
    Aguarda o processamento do ficheiro de áudio/vídeo pela API do Gemini,
    garantindo que se encontra no estado ACTIVE antes da geração.
    """
    print(f"-> A aguardar processamento do ficheiro '{file_ref.display_name}'...")
    while file_ref.state.name == "PROCESSING":
        time.sleep(3)
        file_ref = client.files.get(name=file_ref.name)

    if file_ref.state.name != "ACTIVE":
        raise RuntimeError(
            f"Falha no processamento do ficheiro: {file_ref.state.name} - "
            f"{getattr(file_ref, 'error', 'Erro desconhecido')}"
        )

    print("-> Ficheiro pronto e ativo para análise.")
    return file_ref


def process_meeting_media(file_path: str):
    """
    Carrega o ficheiro de áudio/vídeo, transcreve e extrai tópicos
    e participantes utilizando o gemini-2.5-flash.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro multimédia não encontrado em: {file_path}")

    print(f"\n[1/3] A carregar ficheiro para a Google Files API: {path.name}...")

    # 3. Upload do ficheiro através da Files API
    uploaded_file = client.files.upload(file=str(path))
    print(f"-> Ficheiro carregado com URI: {uploaded_file.uri}")

    # Garante que o ficheiro concluiu a codificação interna
    uploaded_file = wait_for_file_processing(uploaded_file)

    try:
        # 4. Prompt estruturado com instruções para a IA
        prompt = """
        Aja como o motor de inteligência de reuniões do SmartMeeting.
        Analise atentamente o áudio/vídeo fornecido e gere um relatório estruturado em português com o seguinte formato:

        1. PARTICIPANTES IDENTIFICADOS:
           - Identifique cada interveniente e o respetivo papel/contexto (ou 'Orador 1', 'Orador 2', se os nomes não forem referidos).

        2. TÓPICOS PRINCIPAIS & DECISÕES:
           - Síntese dos assuntos debatidos organizados por tópicos.
           - Decisões concretas tomadas pelo grupo.

        3. MAPA DE DISTRIBUIÇÃO DE TAREFAS (AÇÕES):
           - Tarefa / Entregável
           - Responsável (se atribuído)
           - Prazo ou Estimativa (se mencionada)
           - Nível de Prioridade (Baixa / Média / Alta / Urgente)

        4. TRANSCRIÇÃO DETALHADA COM TIMESTAMPS:
           - Transcreva a conversa com a marcação de tempo (ex: [00:15] Orador: texto).
        """

        print("[2/3] A enviar para o modelo gemini-2.5-flash...")

        # Chamada ao modelo Gemini 2.5 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.2,  # Baixa temperatura para transcrição mais fidedigna
            ),
        )

        # 5. Impressão do resultado na consola
        print("\n[3/3] ================= RELATÓRIO SMARTMEETING =================")
        print(response.text)
        print("=================================================================\n")

        return response.text

    finally:
        # Boas práticas: limpeza do ficheiro na nuvem após o processamento
        try:
            print("-> A limpar ficheiro temporário dos servidores do Gemini...")
            client.files.delete(name=uploaded_file.name)
            print("-> Limpeza concluída.")
        except Exception as e:
            print(f"Aviso ao eliminar ficheiro remoto: {e}")


if __name__ == "__main__":
    # Permite passar o caminho do ficheiro por argumento ou usa um padrão
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Substitua pelo caminho do seu ficheiro .mp3, .wav ou .mp4
        target_file = "reuniao_exemplo.mp3"

    print(f"SmartMeeting AI Engine iniciado. Ficheiro: {target_file}")
    process_meeting_media(target_file)