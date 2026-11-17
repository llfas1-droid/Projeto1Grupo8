import os
import requests # Nova biblioteca que instalaste
from dotenv import load_dotenv

# 1. Carrega as variáveis de ambiente a partir do ficheiro .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("A variável GEMINI_API_KEY não foi encontrada no ficheiro .env.")

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

3. MAPA DE AÇÕES E ENTREGÁVEIS (DISTRIBUIÇÃO DE TAREFAS)
    É OBRIGATÓRIO apresentar esta secção exclusivamente numa tabela Markdown estruturada, com as seguintes colunas:
    | Tarefa / Entregável | Responsável | Prazo / Data Limite | Prioridade |
    |---|---|---|---|
"""

def process_meeting_text(transcricao: str) -> str:
    print("-> A enviar pedido para a API (limite máximo de 15 segundos)...")
    prompt = f"{SYSTEM_INSTRUCTION}\n\n--- INÍCIO DA TRANSCRIÇÃO ---\n{transcricao}\n--- FIM DA TRANSCRIÇÃO ---"
    
    # URL direto para o modelo exato que pediste
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        # O timeout=15 impede que o terminal fique encravado infinitamente
        resposta = requests.post(url, json=payload, timeout=15)
        
        # Se a resposta for 200 (OK), devolve o texto
        if resposta.status_code == 200:
            dados = resposta.json()
            return dados['candidates'][0]['content']['parts'][0]['text']
        else:
            # Se o modelo falhar (ex: nome inválido ou servidor ocupado), mostra o erro cru
            raise RuntimeError(f"ERRO DA API ({resposta.status_code}): {resposta.text}")
            
    except requests.exceptions.Timeout:
        return "ERRO: O servidor da Google não respondeu ao fim de 15 segundos (Timeout)."
    except Exception as e:
        return f"ERRO: {str(e)}"

if __name__ == "__main__":
    print("A processar a transcrição da reunião...\n")
    resultado = process_meeting_text(TRANSCRICAO_EXEMPLO)

    print("=" * 65)
    print("        SMARTMEETING · RELATÓRIO EXECUTIVO DA REUNIÃO")
    print("=" * 65)
    print(resultado)
    print("=" * 65)