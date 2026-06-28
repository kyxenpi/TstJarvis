from typing import List, Dict, Any, Tuple
from config import settings
from agent.models import model_manager
from agent.executor import tool_executor
from agent.context import ContextManager
from agent.reflection import ReflectionEngine
from database.memory_db import db
from core.logger import setup_logger
from tools.base import registry, IS_CLOUD  # Importa o registro e a flag de ambiente

logger = setup_logger("AgentCore")

class Agent:
    def __init__(self) -> None:
        self.max_steps = settings.MAX_AGENT_STEPS

    def process(self, session_id: str, user_message: str) -> Tuple[str, List[Dict[str, Any]]]:
        print("\n" + "="*60)
        print(f"📥 [ENTRADA USUÁRIO]: '{user_message}'")
        print("="*60)
        
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
            
            # --- CASO A RESPOSTA SEJA UMA CHAMADA DE FERRAMENTA ---
            if tool_call and "tool" in tool_call:
                tool_name = tool_call["tool"]
                tool_args = tool_call.get("args", {})
                comentario = tool_call.get("comentario", "Sem comentário.")

                # Se a ferramenta for 'none', ignora e trata como conversa pura
                if str(tool_name).lower() == "none":
                    print("⚠️ [AVISO] Modelo gerou ferramenta 'none'. Ignorando e tratando como texto.")
                    tool_call = None
                    continue

                # 🛑 BLINDAGEM DE AMBIENTE: Impede a execução se o LLM tentar alucinar ou forçar uma ferramenta local na nuvem
                if tool_name not in registry.tools or (IS_CLOUD and not registry.tools[tool_name]["cloud_compatible"]):
                    print(f"🚫 [SEGURANÇA] LLM tentou chamar ferramenta indisponível na nuvem: '{tool_name}'")
                    db.save_message(session_id, "user", f"[Sistema]: A ferramenta '{tool_name}' não está disponível neste ambiente (Nuvem). Não tente chamá-la de novo. Resolva o problema usando apenas texto ou ferramentas cloud disponíveis.")
                    continue

                # 🛑 TRAVA ANTILOOP: Evita chamar a mesma ferramenta com mesmos argumentos em sequência
                if execution_flow and execution_flow[-1].get("tool_name") == tool_name and execution_flow[-1].get("tool_args") == tool_args:
                    print(f"⚠️ [TRAVA DE LOOP] Detectada chamada repetida de '{tool_name}'. Interrompendo redundância.")
                    db.save_message(session_id, "user", f"[Sistema]: Você já executou '{tool_name}' e obteve os dados acima. NÃO chame a ferramenta novamente. Formate a resposta final em texto legível para o usuário imediatamente.")
                    continue

                print(f"🎯 [JSON PARSEADO]:")
                print(f"   ├─ Comentário: {comentario}")
                print(f"   ├─ Ferramenta: {tool_name}")
                print(f"   └─ Argumentos: {tool_args}")

                execution_flow.append({
                    "type": "jarvis", 
                    "content": f"{comentario}",
                    "tool_name": tool_name,
                    "tool_args": tool_args
                })
                
                print(f"⚙️ [EXECUÇÃO] Disparando '{tool_name}'...")
                result = tool_executor.execute(tool_name, tool_args)
                
                saida_tool = result.output if result.success else result.error
                print(f"   └─ Saída da Tool: {saida_tool}")

                execution_flow.append({
                    "type": "tool", 
                    "content": f"⚡ `[System]: {tool_name} executado.`"
                })

                # Mudamos o papel para 'user' para melhorar o entendimento contextual da Groq
                db.save_message(session_id, "user", f"Resultado da ferramenta '{tool_name}': {saida_tool}")
                
                continue

            # --- CASO A RESPOSTA SEJA CONVERSA PURA (TEXTO FINAL PARA O USUÁRIO) ---
            else:
                # ⚡ ATALHO PARA ECONOMIA DE TOKENS: Conversa simples na primeira iteração pula o validador
                if step == 1:
                    print("💬 [CONVERSA DIRETA] Resposta em texto puro no ciclo 1. Encerrando de imediato.")
                    execution_flow.append({"type": "jarvis", "content": ai_response})
                    final_text = ai_response
                    break

                print("🧐 [REFLEXÃO] Verificando se a resposta cumpre o objetivo...")
                meta_atingida = ReflectionEngine.verify_goal(user_message, ai_response)
                
                if meta_atingida:
                    print("✅ Objetivo cumprido de forma satisfatória.")
                    print("💬 [CONVERSA PURA] Encerrando ciclo.")
                    execution_flow.append({"type": "jarvis", "content": ai_response})
                    final_text = ai_response
                    break
                else:
                    print("⚠️ [REFLEXÃO] Resposta incompleta ou inválida. Forçando o modelo a revisar no próximo ciclo...")
                    db.save_message(session_id, "system", "Sua resposta anterior não concluiu o objetivo de forma satisfatória ou faltou listar os dados recebidos. Reformule e apresente os dados ao usuário de forma amigável.")
                    execution_flow.append({"type": "jarvis", "content": "Ajustando resposta..."})
                    continue

        # Fallback de segurança caso estoure o número máximo de iterações
        if not final_text and execution_flow:
            for item in reversed(execution_flow):
                if item["type"] == "jarvis" and len(item["content"]) > 30:
                    final_text = item["content"]
                    break
            if not final_text:
                final_text = "Processamento concluído, mas não consegui formatar a resposta a tempo."

        db.save_message(session_id, "assistant", final_text)
        print("="*60 + "\n")
        return final_text, execution_flow

koda_agent = Agent()