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
        print(f"\n{'='*60}")
        print(f"📥 [ENTRADA]: '{user_message}'")
        print(f"{'='*60}")

        db.save_message(session_id, "user", user_message)

        execution_flow: List[Dict[str, Any]] = []
        step = 0
        final_text = ""
        last_tool_call = None

        while step < self.max_steps:
            step += 1
            print(f"\n🧠 [CICLO {step}/{self.max_steps}]")

            context = ContextManager.build(session_id)

            try:
                resposta = model_manager.execute_completion(context)
            except Exception as e:
                print(f"❌ [ERRO LLM]: {e}")
                return "Erro nos motores de IA. Tente novamente.", []

            tool_call = tool_executor.extract_tool_calls(resposta)

            if tool_call and "tool_calls" in tool_call:
                comentario = tool_call.get("comentario", "Executando ferramentas.")
                print(f"🎯 [FERRAMENTAS]: {comentario}")

                execution_flow.append({
                    "type": "jarvis",
                    "content": comentario
                })

                tool_results = []
                nova_chamada = None

                for call in tool_call["tool_calls"]:
                    tool_name = call.get("tool", "")
                    tool_args = call.get("args", {})

                    print(f"\n⚙️ [{tool_name}] args: {tool_args}")

                    if tool_name not in registry.tools:
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Ferramenta inexistente."
                        })
                        continue

                    if IS_CLOUD and not registry.tools[tool_name]["cloud_compatible"]:
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Indisponível na nuvem."
                        })
                        continue

                    chave = (tool_name, str(tool_args))
                    if chave == last_tool_call:
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": "Chamada repetida consecutiva."
                        })
                        continue
                    last_tool_call = chave

                    execution_flow.append({
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": tool_args
                    })

                    result = tool_executor.execute(tool_name, tool_args)
                    tool_results.append({
                        "tool": tool_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error
                    })

                    print(f"   ↳ {'✅' if result.success else '❌'} {result.output or result.error}")

                    if tool_executor.extract_tool_calls(result.output):
                        nova_chamada = result.output

                print(f"\n📦 Resultados enviados para análise do modelo.")
                db.save_message(
                    session_id,
                    "system",
                    "Resultado das ferramentas:\n" + json.dumps(tool_results, ensure_ascii=False, indent=2)
                )

                execution_flow.append({
                    "type": "tool_results",
                    "content": tool_results
                })

                if nova_chamada:
                    db.save_message(session_id, "system",
                        "Nota: Uma ferramenta retornou uma solicitação de nova ferramenta. Processe se necessário.")

                if step >= self.max_steps:
                    last_tool = tool_results[-1] if tool_results else {}
                    final_text = last_tool.get("output") or last_tool.get("error") or "Execução concluída."
                    break

                continue

            else:
                if step == 1:
                    print(f"💬 [RESPOSTA DIRETA]")
                    execution_flow.append({"type": "jarvis", "content": resposta})
                    final_text = resposta
                    break

                print(f"🧐 [REFLEXÃO]")
                meta = ReflectionEngine.verify_goal(user_message, resposta)

                if meta:
                    print(f"✅ Objetivo concluído.")
                    execution_flow.append({"type": "jarvis", "content": resposta})
                    final_text = resposta
                    break

                print(f"⚠️ Incompleto. Revisando...")
                db.save_message(
                    session_id, "system",
                    "Sua resposta não concluiu o objetivo. Use os resultados das ferramentas e responda."
                )
                execution_flow.append({"type": "jarvis", "content": "Reavaliando..."})

        if not final_text and execution_flow:
            for item in reversed(execution_flow):
                if item["type"] == "jarvis" and isinstance(item["content"], str) and len(item["content"]) > 30:
                    final_text = item["content"]
                    break
            if not final_text:
                final_text = "Processamento concluído, mas não consegui formatar a resposta."

        db.save_message(session_id, "assistant", final_text)
        print(f"\n{'='*60}\n")

        return final_text, execution_flow


koda_agent = Agent()
