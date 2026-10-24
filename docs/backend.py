import os
from dotenv import load_dotenv
from google import genai

# Carrega a chave do ficheiro .env
pasta_atual = os.path.dirname(os.path.abspath(__file__))
caminho_env = os.path.join(pasta_atual, '.env')
load_dotenv(caminho_env)

chave_api = os.environ.get("GEMINI_API_KEY")

print("✅ Chave encontrada com sucesso! A ligar à IA...")

client = genai.Client(api_key=chave_api)

instrucoes_smartmeeting = """
Atua como o sistema SmartMeeting. Lê a seguinte transcrição:
"João: Precisamos que a página de login esteja pronta amanhã.
Maria: Ok, eu faço o design da interface hoje.
Pedro: Eu trato da ligação segura à base de dados."

Gera:
1. Resumo da reunião.
2. Mapa de Tarefas (Quem faz o quê).
"""

# Usa o modelo mais recente que o seu sistema exige
interaction = client.interactions.create(
    model='models/gemini-3.8-flash',
    input=instrucoes_smartmeeting,
    generation_config={
        'max_output_tokens': 8192,
        'thinking_level': 'medium',
    }
)

print("\n=== RESULTADO SMARTMEETING ===")
# Imprime a resposta final gerada pela IA
print(interaction.steps[-1])