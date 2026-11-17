import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()


def agrupar_tarefas_por_funcionario(dados_reuniao: dict) -> dict:
    """
    Agrupa as tarefas validadas por cada responsável, cruzando com a respetiva
    função e e-mail definidos na lista de participantes.
    """
    participantes_info = {}
    for p in dados_reuniao.get("participantes", []):
        nome = p.get("nome", "").strip()
        if nome:
            participantes_info[nome.lower()] = {
                "nome": nome,
                "funcao": p.get("funcao", "Membro da Equipa"),
                "email": p.get("email", ""),
            }

    notificacoes_por_pessoa = {}

    for tarefa in dados_reuniao.get("tarefas", []):
        responsavel = tarefa.get("responsavel", "").strip()
        if not responsavel:
            continue

        chave = responsavel.lower()
        info = participantes_info.get(
            chave,
            {"nome": responsavel, "funcao": "Membro da Equipa", "email": ""},
        )

        if chave not in notificacoes_por_pessoa:
            notificacoes_por_pessoa[chave] = {
                "nome": info["nome"],
                "funcao": info["funcao"],
                "email": info["email"],
                "tarefas": [],
            }

        notificacoes_por_pessoa[chave]["tarefas"].append(tarefa)

    return notificacoes_por_pessoa


def formatar_mensagem_notificacao(dados_funcionario: dict) -> str:
    """
    Constrói o texto personalizado da notificação com a função do funcionário
    e a lista detalhada das suas tarefas aprovadas.
    """
    nome = dados_funcionario["nome"]
    funcao = dados_funcionario["funcao"]
    tarefas = dados_funcionario["tarefas"]

    linhas = [
        f"Olá {nome},",
        "",
        "O gerente validou o plano de ação da última reunião no SmartMeeting.",
        f"A tua função registada: {funcao}",
        "",
        "As tuas tarefas atribuídas são:",
    ]

    for idx, t in enumerate(tarefas, start=1):
        descricao = t.get("descricao", "Tarefa sem descrição")
        prazo = t.get("prazo", "Sem prazo definido")
        prioridade = t.get("prioridade", "Normal")
        linhas.append(
            f"  {idx}. {descricao} | Prazo: {prazo} | Prioridade: {prioridade}"
        )

    linhas.extend(
        [
            "",
            "Por favor, atualiza o estado das tarefas assim que estiverem concluídas.",
            "Equipa SmartMeeting",
        ]
    )

    return "\n".join(linhas)


def enviar_email_smtp(destinatario_email: str, assunto: str, corpo: str) -> None:
    """
    Envia um e-mail real através de servidor SMTP configurado no .env.
    """
    remetente = os.getenv("EMAIL_REMETENTE")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not remetente or not password:
        raise ValueError(
            "Credenciais SMTP ausentes. Configure EMAIL_REMETENTE e EMAIL_PASSWORD no .env."
        )

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario_email
    msg.set_content(corpo)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(remetente, password)
        server.send_message(msg)


def disparar_alertas_reuniao(dados_reuniao: dict, modo_teste: bool = True) -> list:
    """
    Verifica se o gerente aprovou as tarefas e envia os alertas automáticos
    individuais para cada funcionário responsável.
    """
    if not dados_reuniao.get("aprovado_gerente", False):
        print("⛔ Envio bloqueado: As tarefas ainda aguardam validação do gerente.")
        return []

    print("✅ Aprovação do gerente confirmada. A preparar notificações...")
    agrupado = agrupar_tarefas_por_funcionario(dados_reuniao)
    alertas_enviados = []

    for dados_func in agrupado.values():
        mensagem = formatar_mensagem_notificacao(dados_func)
        assunto = f"[SmartMeeting] Tarefas Atribuídas ({dados_func['funcao']})"

        if modo_teste:
            print("\n" + "=" * 55)
            print(f"PARA: {dados_func['nome']} <{dados_func['email'] or 'sem-email@empresa.pt'}>")
            print(f"ASSUNTO: {assunto}")
            print("-" * 55)
            print(mensagem)
            print("=" * 55)
        else:
            if not dados_func["email"]:
                print(f"⚠️ Aviso: {dados_func['nome']} não tem e-mail registado. Envio ignorado.")
                continue
            enviar_email_smtp(dados_func["email"], assunto, mensagem)
            print(f"📧 Alerta enviado com sucesso para {dados_func['nome']} ({dados_func['email']}).")

        alertas_enviados.append(
            {
                "destinatario": dados_func["nome"],
                "funcao": dados_func["funcao"],
                "total_tarefas": len(dados_func["tarefas"]),
            }
        )

    return alertas_enviados


if __name__ == "__main__":
    # Exemplo de dados após análise da reunião e validação pelo gerente
    reuniao_exemplo = {
        "aprovado_gerente": True,
        "participantes": [
            {"nome": "Ana", "funcao": "Gestora de Projeto", "email": "ana@empresa.pt"},
            {"nome": "Rui", "funcao": "Programador Backend", "email": "rui@empresa.pt"},
            {"nome": "Marta", "funcao": "Designer Frontend", "email": "marta@empresa.pt"},
        ],
        "tarefas": [
            {
                "descricao": "Concluir integração da API Gemini",
                "responsavel": "Rui",
                "prazo": "Quinta-feira",
                "prioridade": "Alta",
            },
            {
                "descricao": "Desenvolver ecrã de visualização do resumo",
                "responsavel": "Marta",
                "prazo": "Quinta-feira à noite",
                "prioridade": "Alta",
            },
            {
                "descricao": "Testar envio automático de notificações",
                "responsavel": "Rui",
                "prazo": "Sexta-feira",
                "prioridade": "Média",
            },
        ],
    }

    print("SmartMeeting Notificador iniciado.")
    disparar_alertas_reuniao(reuniao_exemplo, modo_teste=True)