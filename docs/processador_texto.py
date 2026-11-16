import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai._gaos.lib.compat_errors import InternalServerError

# 1. Carrega as variáveis de ambiente a partir do ficheiro .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(
        "A variável GEMINI_API_KEY não foi encontrada no ficheiro .env. "
        "Adicione: GEMINI_API_KEY='a_sua_chave' ao seu .env."
    )

# 2. Inicializa o cliente oficial da Google GenAI
client = genai.Client(api_key=api_key)

# 3. Transcrição de exemplo de uma reunião de alinhamento de equipa
TRANSCRICAO_EXEMPLO = """
[00:02] Ana (Tech Lead): Bom dia a todos. O objetivo da reunião de hoje é fechar os bloqueios para o lançamento da nova funcionalidade de pagamentos e rever prazos.
[00:18] Carlos (Backend): Pelo lado do backend, a integração com o Stripe está a 85%. No entanto, estamos a ter timeouts nas chamadas ao webhook quando o volume de transações sobe. O prazo inicial de entrega era esta sexta-feira, mas sem resolver isto corremos risco de falhas em produção.
[00:45] Mariana (Frontend): No frontend, as telas do checkout e tratamento de erros estão concluídas. Só precisamos que o Carlos estabilize os contratos da API até quinta ao final do dia para podermos ligar os fluxos finais e testar.
[01:10] Pedro (QA): Se recebermos o ambiente pronto até sexta-feira de manhã, conseguimos executar os testes de regressão durante o fim de semana e segunda-feira. Se atrasar além disso, o release terá de ser adiado para o sprint seguinte.
[01:30] Ana (Tech Lead): Entendido. Carlos, podes colocar o Diogo a ajudar-te a otimizar as queries da base de dados e a fila de processamento do webhook hoje à tarde. A prioritária máxima passa a ser este bloqueio.
[01:48] Carlos (Backend): Perfeito, alinho com o Diogo logo a seguir ao almoço. Garanto os endpoints corrigidos até quinta-feira às 18h.
[02:05] Mariana (Frontend): Combinado. Assim que o Carlos subir para o ambiente de staging, eu e o Pedro fazemos um sanity check juntos.
[02:18] Ana (Tech Lead): Excelente. Ficou também pendente a questão da documentação da API para o cliente corporativo. Mariana, podes assumir a atualização do Swagger?
[02:30] Mariana (Frontend): Sim, trato disso na sexta-feira de manhã enquanto o QA inicia os testes.
[02:40] Ana (Tech Lead): Ótimo. Ficamos então assim alinhados. Obrigado a todos.
"""

# 4. System Instruction para padronizar e estruturar a análise da reunião
SYSTEM_INSTRUCTION = """
És o assistente de inteligência e governança do SmartMeeting.
A tua função é analisar a transcrição de uma reunião de trabalho e gerar um resumo estruturado, objetivo e profissional em português.

Apresenta a tua análise exatamente com esta estrutura:

1. VISÃO GERAL
    - Objetivo principal da reunião em 1 ou 2 frases curtas.

2. TÓPICOS DISCUTIDOS & DECISÕES
    Para cada assunto identificado, detalha:
    - Tópico: Nome descritivo do assunto.
    - Contexto & Bloqueios: O problema ou situação abordada.
    - Decisão / Conclusão: O que ficou acordado ou resolvido.

3. MAPA DE AÇÕES E ENTREGÁVEIS
    Lista em tabela ou marcadores:
    - Tarefa
    - Responsável
    - Prazo / Data limite
    - Nível de Prioridade (Baixa, Média, Alta ou Crítica)
"""


def process_meeting_text(transcricao: str) -> str:
    prompt = f"{SYSTEM_INSTRUCTION}\n\n--- INÍCIO DA TRANSCRIÇÃO ---\n{transcricao}\n--- FIM DA TRANSCRIÇÃO ---"

    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            # Utiliza a API de interações que confirmámos funcionar no seu sistema
            interaction = client.interactions.create(
                model='models/gemini-3.8-flash',
                input=prompt
            )
            return str(interaction.steps[-1])
        except InternalServerError as e:
            if tentativa < max_tentativas:
                print(f"⚠️ Servidor ocupado (503). A tentar novamente em 3 segundos (Tentativa {tentativa}/{max_tentativas})...")
                time.sleep(3)
            else:
                raise e


if __name__ == "__main__":
    print("A processar a transcrição da reunião com o Gemini 3.8 Flash...\n")
    resultado = extrair_topicos_e_resumo(TRANSCRICAO_EXEMPLO)

    # 5. Impressão do resultado formatado na consola
    print("=" * 65)
    print("        SMARTMEETING · RELATÓRIO EXECUTIVO DA REUNIÃO")
    print("=" * 65)
    print(resultado)
    print("=" * 65)