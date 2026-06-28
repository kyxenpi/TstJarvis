import os
import json
import requests
from flask import Blueprint, request
from agent.agent import koda_agent
from agent.executor import tool_executor
from config import settings

telegram_blueprint = Blueprint('telegram', __name__)

@telegram_blueprint.route('/webhook', methods=['POST'])
def telegram_webhook():
    # Tenta pegar das configurações, se falhar puxa do os.getenv como o antigo fazia
    token = getattr(settings, 'TELEGRAM_TOKEN', None) or os.getenv("TELEGRAM_TOKEN", "")
    
    if not token:
        print("❌ [TELEGRAM CRÍTICO]: TELEGRAM_TOKEN está VAZIO!")
        return 'Token não configurado', 500

    try:
        # Fallback idêntico ao seu antigo para garantir que os dados sejam lidos sempre
        dados_update = request.get_json(silent=True) or json.loads(request.data.decode('utf-8'))
        
        if dados_update and "message" in dados_update and "text" in dados_update["message"]:
            chat_id = str(dados_update["message"]["chat"]["id"])
            texto_usuario = dados_update["message"]["text"]
            
            print(f"📩 [TELEGRAM]: Mensagem recebida: '{texto_usuario}' do Chat ID: {chat_id}")
            
            base_url = f"https://api.telegram.org/bot{token}"
            
            # Feedback visual de digitação
            try:
                requests.post(f"{base_url}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
            except Exception as e:
                print(f"⚠️ [TELEGRAM WARNING]: Falha ao enviar 'typing': {e}")
                
            # Executa o novo motor do agente
            resposta_texto, fluxo = koda_agent.process(chat_id, texto_usuario)
            
            # Envia atualizações de ferramentas em tempo real para o chat
            for etapa in fluxo:
                if etapa["type"] == "tool":
                    try:
                        requests.post(f"{base_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": etapa["content"],
                            "parse_mode": "Markdown"
                        }, timeout=5)
                    except Exception as e:
                        print(f"❌ [TELEGRAM ERROR]: Falha ao enviar log de tool: {e}")

            # Envia o texto definitivo se não for JSON estruturado
            if not tool_executor.parse_json_safely(resposta_texto):
                
                # Defesa contra loops longos mantida do seu antigo
                if len(resposta_texto) > 1000:
                    resposta_texto = (
                        "⚠️ *[Koda detectou um comportamento instável e cortou a resposta]:*\n\n" + 
                        resposta_texto[:400] + "...\n\n" +
                        "_O modelo estourou o limite de texto em loop. Reordene o comando de forma clara._"
                    )
                
                print(f"📤 [TELEGRAM ENVIO]: Enviando resposta final para o chat {chat_id}")
                res = requests.post(f"{base_url}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": resposta_texto,
                    "parse_mode": "Markdown"
                }, timeout=5)
                print(f"   └─ Status: {res.status_code}")

        return 'OK', 200
    except Exception as e:
        print(f"❌ [TELEGRAM CRASH]: Erro bruto no processamento do Webhook: {e}")
        return 'Erro Interno', 500