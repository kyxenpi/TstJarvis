import json
from typing import List, Dict, Any, Tuple

from config import settings
from agent.models import model_manager
from agent.executor import tool_executor
from agent.context import ContextManager
from agent.reflection import ReflectionEngine
from database.memory_db import db
from core.logger import setup_logger
from tools.base import registry, IS_CLOUD

logger = setup_logger("AgentCore")


class Agent:
    def __init__(self) -> None:
        self.max_steps = settings.MAX_AGENT_STEPS

    def process(self, session_id: str, user_message: str) -> Tuple[str, List[Dict[str, Any]]]:
        print("\n" + "=" * 60)
        print(f"📥 [ENTRADA USUÁRIO]: '{user_message}'")
        print("=" * 60)

        db.save_message(session_id, "user", user_message)

        execution_flow: List[Dict[str, Any]] = []
        step = 0
        final_text = ""

        while step < self.max_steps:
            step += 1

            print(f"\n🧠 [CICLO COGNITIVO {step}/{self.max_steps}] Chamando LLM...")

            api_context = ContextManager.build(session_id)

            try:
                ai_response = model_manager.execute_completion(api_context)

                print("\n--- [RESPOSTA BRUTA DO MODELO] ---")
                print(ai_response)
                print("----------------------------------")

            except Exception as e:
                print(f"❌ [ERRO LLM]: {e}")
                return "Deu ruim nos meus motores aqui.", []

            tool_call = tool_executor.parse_json_safely(ai_response)

            # ==========================
            # CHAMADA DE FERRAMENTAS
            # ==========================

            if tool_call and "tool_calls" in tool_call:

                comentario = tool_call.get(
                    "comentario",
                    "Executando ferramentas."
                )

                print("🎯 [JSON PARSEADO]")
                print(f"   └─ {comentario}")

                execution_flow.append({
                    "type": "jarvis",
                    "content": comentario
                })

                tool_results = []

                for call in tool_call["tool_calls"]:

                    tool_name = call["tool"]
                    tool_args = call.get("args", {})

                    print(f"\n⚙️ [EXECUÇÃO] {tool_name}")
                    print(f"   Args: {tool_args}")

                    # ferramenta inexistente
                    if tool_name not in registry.tools:
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Ferramenta inexistente."
                        })
                        continue

                    # ambiente cloud
                    if (
                        IS_CLOUD
                        and not registry.tools[tool_name]["cloud_compatible"]
                    ):
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Ferramenta indisponível na nuvem."
                        })
                        continue

                    # procura a última tool executada
                    ultima_tool = next(
                        (
                            item
                            for item in reversed(execution_flow)
                            if item["type"] == "tool_call"
                        ),
                        None
                    )

                    # anti-loop
                    if (
                        ultima_tool
                        and ultima_tool["tool_name"] == tool_name
                        and ultima_tool["tool_args"] == tool_args
                    ):
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Chamada repetida."
                        })
                        continue

                    execution_flow.append({
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": tool_args
                    })

                    result = tool_executor.execute(
                        tool_name,
                        tool_args
                    )

                    tool_results.append({
                        "tool": tool_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error
                    })

                    print(
                        f"   Resultado: "
                        f"{result.output if result.success else result.error}"
                    )

                # Envia todos os resultados para o modelo de uma vez
                db.save_message(
                    session_id,
                    "user",
                    "Resultado das ferramentas:\n"
                    + json.dumps(
                        tool_results,
                        ensure_ascii=False,
                        indent=2
                    )
                )

                execution_flow.append({
                    "type": "tool_results",
                    "content": tool_results
                })

                # Volta para o modelo analisar os resultados
                continue

            # ==========================
            # CONVERSA NORMAL
            # ==========================

            else:

                # Conversa simples na primeira iteração
                if step == 1:
                    print(
                        "💬 [CONVERSA DIRETA] "
                        "Resposta em texto puro no ciclo 1."
                    )

                    execution_flow.append({
                        "type": "jarvis",
                        "content": ai_response
                    })

                    final_text = ai_response
                    break

                print("🧐 [REFLEXÃO] Verificando objetivo...")

                meta_atingida = ReflectionEngine.verify_goal(
                    user_message,
                    ai_response
                )

                if meta_atingida:

                    print("✅ Objetivo concluído.")

                    execution_flow.append({
                        "type": "jarvis",
                        "content": ai_response
                    })

                    final_text = ai_response

                    break

                print(
                    "⚠️ [REFLEXÃO] "
                    "Resposta incompleta. Solicitando revisão..."
                )

                db.save_message(
                    session_id,
                    "system",
                    (
                        "Sua resposta anterior não concluiu o objetivo. "
                        "Utilize corretamente os resultados das ferramentas "
                        "e responda ao usuário de forma completa."
                    )
                )

                execution_flow.append({
                    "type": "jarvis",
                    "content": "Reavaliando resposta..."
                })

                continue

        # ==========================
        # FALLBACK DE SEGURANÇA
        # ==========================

        if not final_text and execution_flow:

            for item in reversed(execution_flow):

                if (
                    item["type"] == "jarvis"
                    and isinstance(item["content"], str)
                    and len(item["content"]) > 30
                ):
                    final_text = item["content"]
                    break

            if not final_text:
                final_text = (
                    "Processamento concluído, mas não consegui "
                    "formatar a resposta a tempo."
                )

        db.save_message(
            session_id,
            "assistant",
            final_text
        )

        print("=" * 60 + "\n")

        return final_text, execution_flow

koda_agent = Agent()