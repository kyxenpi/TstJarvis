from agent.models import model_manager
import json

class ReflectionEngine:
    @staticmethod
    def verify_goal(user_intent: str, last_output: str) -> bool:
        # Se a saída for vazia, o objetivo NÃO foi cumprido
        if not last_output or not last_output.strip():
            return False
            
        # IMPORTANTE: Se a última saída for puramente um bloco JSON de ferramenta, 
        # significa que o Koda apenas DISPAROU uma ação, mas ainda não deu a resposta
        # final em texto para o usuário. Portanto, o objetivo ainda NÃO foi cumprido.
        trimmed_output = last_output.strip()
        if trimmed_output.startswith("{") and trimmed_output.endswith("}"):
            try:
                # Se for um JSON válido contendo a chave 'tool', não encerra o ciclo
                dados = json.loads(trimmed_output)
                if "tool" in dados:
                    return False
            except:
                pass

        last_output_lower = last_output.lower()
        erros_criticos = ["indisponível", "erro", "failed", "error", "não encontrada", "indisponivel"]
        if any(erro in last_output_lower for erro in erros_criticos):
            return False

        # Se passou pelos erros e é uma resposta em texto para o usuário, validamos semanticamente
        prompt = [
        {
            "role": "system", 
            "content": (
                "Você é um validador lógico estrito de interações entre humanos e IA.\n"
                "Analise se a resposta do assistente atende adequadamente a intenção do usuário.\n\n"
                "CRITÉRIOS:\n"
                "1. Se a intenção do usuário for apenas uma saudação, conversa casual ou frase curta (ex: 'Olá', 'Bom dia', 'Tudo bem?'), "
                "qualquer resposta cumpre 100% o objetivo.\n"
                "2. Se a intenção envolver uma tarefa/comando, a resposta deve conter o resultado ou a conclusão dela.\n\n"
                "Responda estritamente com 'SIM' ou 'NAO' (sem justificativas)."
            )
        },
        {
            "role": "user", 
            "content": f"Intenção do Usuário: \"{user_intent}\"\nResposta do Assistente: \"{last_output}\"\nO objetivo foi cumprido?"
        }
    ]
        
        try:
            verificacao = model_manager.execute_completion(prompt, temperature=0.0)
            return "SIM" in verificacao.upper()
        except:
            # Em automações complexas em cadeia, se a API de reflexão cair,
            # retornamos False para permitir que o loop continue tentando.
            return False