#!/usr/bin/env python3
"""
SmartMeeting - Orquestrador Principal (backend.py)
Fluxo completo:
1. Deteta o tipo de ficheiro (Texto ou Multimédia)
2. Executa processador_texto.py ou processador_media.py
3. Normaliza o resultado para JSON estruturado (participantes e tarefas)
4. Abre a revisão interativa do gerente no terminal (Issue 9)
5. Dispara notificações consolidadas via notificador.py após aprovação (Issue 10)
"""

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from processador_media import process_meeting_media
from notificador import enviar_notificacoes_aprovadas

# Compatibilidade automática com o nome da função em processador_texto.py
try:
    from processador_texto import process_meeting_text
except ImportError:
    from processador_texto import extrair_topicos_e_resumo as process_meeting_text

load_dotenv()

EXTENSOES_TEXTO = {".txt", ".md"}
EXTENSOES_MEDIA = {".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mpeg", ".mov"}


def estruturar_dados_para_aprovacao(
    resultado_bruto: Any,
    nome_ficheiro: str,
) -> Dict[str, Any]:
    """
    Garante que a saída do processador (seja dict ou texto/Markdown do Gemini)
    fica no formato de dicionário exigido pelo fluxo de aprovação e pelo notificador.py.
    """
    if isinstance(resultado_bruto, dict) and "tarefas" in resultado_bruto:
        resultado_bruto.setdefault("aprovado_gerente", False)
        return resultado_bruto

    texto_analise = str(resultado_bruto)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ficheiro .env.")

    client = genai.Client(api_key=api_key)

    prompt_estruturacao = f"""
    Converte o seguinte relatório/análise de reunião num JSON estrito.
    Se algum e-mail não estiver explícito no texto, gera um e-mail corporativo provisório
    no formato "nome.apelido@empresa.pt" (em minúsculas, sem acentos) para permitir a revisão do gerente.

    Texto da reunião:
    ---
    {texto_analise}
    ---

    Responde APENAS com JSON válido seguindo exatamente esta estrutura:
    {{
      "titulo_reuniao": "Título descritivo da reunião",
      "data": "{date.today().isoformat()}",
      "aprovado_gerente": false,
      "participantes": [
        {{
          "nome": "Nome do Participante",
          "email": "email@empresa.pt",
          "funcao": "Função ou Papel identificado na reunião"
        }}
      ],
      "tarefas": [
        {{
          "descricao": "Descrição clara do entregável",
          "responsavel": "Nome do Participante",
          "email_responsavel": "email@empresa.pt",
          "prazo": "YYYY-MM-DD ou texto indicado",
          "prioridade": "Baixa | Média | Alta | Urgente",
          "estado": "pendente"
        }}
      ]
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_estruturacao,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    dados = json.loads(response.text)
    dados.setdefault("titulo_reuniao", f"Reunião ({nome_ficheiro})")
    dados.setdefault("data", date.today().isoformat())
    dados["aprovado_gerente"] = False  # Obriga sempre à validação do gerente
    return dados


def _imprimir_mapa_tarefas(dados: Dict[str, Any]) -> None:
    """Mostra o mapa de tarefas no terminal (Issue 9)."""
    tarefas: List[Dict[str, Any]] = dados.get("tarefas", [])
    print("\n" + "=" * 95)
    print(f" REVISÃO DO GERENTE · {dados.get('titulo_reuniao', 'Reunião')} ({dados.get('data', '')})")
    print("=" * 95)
    print("| ID | Tarefa / Entregável | Responsável | Prazo | Prioridade | Estado |")
    print("|---|---|---|---|---|---|")

    if not tarefas:
        print("| - | Sem tarefas extraídas | - | - | - | - |")
    else:
        for idx, t in enumerate(tarefas, start=1):
            print(
                f"| {idx} | {t.get('descricao', '')} | "
                f"{t.get('responsavel', 'Por atribuir')} | "
                f"{t.get('prazo', 'A definir')} | "
                f"{t.get('prioridade', 'Média')} | "
                f"{t.get('estado', 'pendente')} |"
            )
    print("=" * 95)


def revisao_interativa_gerente(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Painel interativo no terminal (Issue 9):
    Permite ao gerente editar campos ou remover tarefas antes de escrever 'APROVAR'.
    """
    while True:
        _imprimir_mapa_tarefas(dados)
        print("\nOpções do Gerente:")
        print("  • Escreva 'APROVAR' para validar o mapa e enviar notificações.")
        print("  • Escreva 'EDITAR <ID>' (ex: EDITAR 1) para alterar tarefa, responsável ou prazo.")
        print("  • Escreva 'REMOVER <ID>' (ex: REMOVER 2) para descartar uma tarefa.")
        print("  • Escreva 'CANCELAR' para guardar sem aprovar (bloqueia o envio).")

        comando = input("\nAção > ").strip()
        cmd_upper = comando.upper()

        if cmd_upper == "APROVAR":
            for t in dados.get("tarefas", []):
                t["estado"] = "aprovada"
            dados["aprovado_gerente"] = True
            print("\n[OK] Mapa de tarefas APROVADO pelo gerente.")
            return dados

        if cmd_upper == "CANCELAR":
            dados["aprovado_gerente"] = False
            print("\n[INFO] Revisão encerrada sem aprovação.")
            return dados

        if cmd_upper.startswith("REMOVER "):
            try:
                idx = int(comando.split()[1]) - 1
                removida = dados["tarefas"].pop(idx)
                print(f"-> Tarefa removida: {removida.get('descricao')}")
            except (IndexError, ValueError):
                print("[AVISO] ID inválido. Exemplo: REMOVER 1")
            continue

        if cmd_upper.startswith("EDITAR "):
            try:
                idx = int(comando.split()[1]) - 1
                tarefa = dados["tarefas"][idx]
                print(f"\nA editar Tarefa {idx + 1} (prima Enter para manter o valor atual):")

                nova_desc = input(f"  Descrição [{tarefa.get('descricao')}]: ").strip()
                novo_resp = input(f"  Responsável [{tarefa.get('responsavel')}]: ").strip()
                novo_email = input(f"  E-mail [{tarefa.get('email_responsavel', '')}]: ").strip()
                novo_prazo = input(f"  Prazo [{tarefa.get('prazo')}]: ").strip()
                nova_prio = input(f"  Prioridade [{tarefa.get('prioridade')}]: ").strip()

                if nova_desc:
                    tarefa["descricao"] = nova_desc
                if novo_resp:
                    tarefa["responsavel"] = novo_resp
                if novo_email:
                    tarefa["email_responsavel"] = novo_email
                if novo_prazo:
                    tarefa["prazo"] = novo_prazo
                if nova_prio:
                    tarefa["prioridade"] = nova_prio
                tarefa["estado"] = "editada"
            except (IndexError, ValueError):
                print("[AVISO] ID inválido. Exemplo: EDITAR 1")
            continue

        print("[AVISO] Comando não reconhecido. Use APROVAR, EDITAR <ID>, REMOVER <ID> ou CANCELAR.")


def run_smartmeeting(file_path: str, modo_teste: bool = True) -> Dict[str, Any]:
    """Executa todo o pipeline do SmartMeeting para um ficheiro de texto ou multimédia."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro não encontrado em: {file_path}")

    extensao = path.suffix.lower()

    # 1. Processamento inicial consoante o formato
    if extensao in EXTENSOES_TEXTO:
        print("-> Modo Texto detetado. A encaminhar para processador_texto...")
        conteudo = path.read_text(encoding="utf-8")
        resultado_bruto = process_meeting_text(conteudo)
    elif extensao in EXTENSOES_MEDIA:
        print("-> Modo Multimédia detetado. A encaminhar para processador_media...")
        resultado_bruto = process_meeting_media(str(path))
    else:
        raise ValueError(
            f"Formato '{extensao}' não suportado. "
            f"Use texto ({', '.join(EXTENSOES_TEXTO)}) ou multimédia ({', '.join(EXTENSOES_MEDIA)})."
        )

    # 2. Conversão para estrutura JSON padrão
    print("\n-> A estruturar participantes e mapa de tarefas para revisão...")
    dados_reuniao = estruturar_dados_para_aprovacao(resultado_bruto, path.name)

    # 3. Revisão obrigatória do gerente (Issue 9)
    dados_validados = revisao_interativa_gerente(dados_reuniao)

    # 4. Envio de notificações pós-aprovação (Issue 10)
    print("\n-> A acionar módulo notificador...")
    resultado_envio = enviar_notificacoes_aprovadas(
        dados_reuniao=dados_validados,
        modo_teste=modo_teste,
    )

    return {
        "dados_reuniao": dados_validados,
        "notificacoes": resultado_envio,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: py backend.py <caminho_do_ficheiro> [--enviar-real]")
        print("Exemplo áudio (simulação): py backend.py reuniao.mp3")
        print("Exemplo texto (simulação): py backend.py transcricao.txt")
        print("Exemplo envio SMTP real:   py backend.py reuniao.mp3 --enviar-real")
        sys.exit(1)

    target_file = sys.argv[1]
    enviar_real = "--enviar-real" in sys.argv

    print(f"SmartMeeting AI Engine iniciado. Ficheiro: {target_file}")
    print(f"Modo de notificação: {'ENVIO REAL SMTP' if enviar_real else 'SIMULAÇÃO NO TERMINAL (modo_teste=True)'}")

    run_smartmeeting(target_file, modo_teste=not enviar_real)