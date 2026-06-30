import os
import json
import requests
from flask import Blueprint, request
from agent.agent import koda_agent
from agent.executor import tool_executor
from config import settings
# Importa a sua função de processamento de imagem
from agent.image_process import read_image 

telegram_blueprint = Blueprint('telegram', __name__)

@telegram_blueprint.route('/webhook', methods=['POST'])
def telegram_webhook():
    token = getattr(settings, 'TELEGRAM_TOKEN', None) or os.getenv("TELEGRAM_TOKEN", "")
    
    if not token:
        print("❌ [TELEGRAM CRÍTICO]: TELEGRAM_TOKEN está VAZIO!")
        return 'Token não configurado', 500

    try:
        dados_update = request.get_json(silent=True) or json.loads(request.data.decode('utf-8'))
        
        if dados_update and "message" in dados_update:
            message = dados_update["message"]
            chat_id = str(message["chat"]["id"])
            base_url = f"https://api.telegram.org/bot{token}"
            
            texto_usuario = ""
            
            # --- CASO 1: USUÁRIO ENVIOU UMA FOTO ---
            if "photo" in message:
                print("📸 [TELEGRAM]: Foto recebida! Iniciando extração de texto...")
                try:
                    requests.post(f"{base_url}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
                except Exception:
                    pass
                
                # O Telegram envia uma lista com tamanhos diferentes. O último [-1] é o de maior resolução.
                photo_file_id = message["photo"][-1]["file_id"]
                
                # Pega a legenda da foto (se houver) para complementar o prompt do agente
                legenda = message.get("caption", "")
                
                try:
                    # 1. Pede o caminho do arquivo para a API do Telegram
                    res_file = requests.get(f"{base_url}/getFile", params={"file_id": photo_file_id}, timeout=10).json()
                    if res_file.get("ok"):
                        file_path = res_file["result"]["file_path"]
                        download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                        
                        # 2. Baixa o arquivo binário da imagem
                        img_data = requests.get(download_url, timeout=15).content
                        temp_filename = f"temp_{photo_file_id}.jpg"
                        
                        with open(temp_filename, "wb") as f:
                            f.write(img_data)
                        
                        # 3. Executa a sua ferramenta de OCR
                        print(f"⚙️ [OCR]: Processando imagem temporária: {temp_filename}")
                        resultado_ocr = read_image(temp_filename)
                        
                        # Remove o arquivo temporário após o uso
                        if os.path.exists(temp_filename):
                            os.remove(temp_filename)
                        
                        if resultado_ocr.get("success") and resultado_ocr.get("output"):
                            texto_extraido = resultado_ocr["output"]
                            print(f"📝 [OCR SUCESSO]: Texto extraído: '{texto_extraido}'")
                            
                            # Monta o prompt combinando o texto da imagem + instrução/legenda do usuário
                            texto_usuario = f"[Texto extraído da imagem enviada pelo usuário]:\n{texto_extraido}"
                            if legenda:
                                texto_usuario += f"\n\n[Comando/Legenda do usuário]: {legenda}"
                        else:
                            texto_usuario = "[Sistema]: O usuário enviou uma imagem, mas nenhum texto pôde ser extraído dela."
                            if legenda:
                                texto_usuario += f" O usuário deixou a seguinte legenda: {legenda}"
                    else:
                        texto_usuario = "⚠️ [Erro do Sistema]: Não foi possível obter o link da imagem nos servidores do Telegram."
                except Exception as img_err:
                    print(f"❌ [TELEGRAM ERROR]: Falha ao processar a imagem: {img_err}")
                    texto_usuario = "⚠️ [Erro do Sistema]: Falha interna ao processar a sua imagem."

            # --- CASO 2: TEXTO PURO ---
            elif "text" in message:
                texto_usuario = message["text"]
                print(f"📩 [TELEGRAM]: Mensagem de texto recebida: '{texto_usuario}' do Chat ID: {chat_id}")
            
            # Se não for texto nem foto (ex: sticker, audio), ignora para não quebrar
            if not texto_usuario:
                return 'OK', 200

            # --- FLUXO DE RESPOSTA DO AGENTE (Mantido o seu padrão original) ---
            try:
                requests.post(f"{base_url}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
            except Exception as e:
                print(f"⚠️ [TELEGRAM WARNING]: Falha ao enviar 'typing': {e}")
                
            resposta_texto, fluxo = koda_agent.process(chat_id, texto_usuario)
            
            for etapa in fluxo:
                if etapa["type"] in ("jarvis", "tool_call") and etapa.get("content"):
                    try:
                        requests.post(f"{base_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": etapa["content"],
                            "parse_mode": "Markdown"
                        }, timeout=5)
                    except Exception as e:
                        print(f"❌ [TELEGRAM ERROR]: Falha ao enviar msg: {e}")

            if not tool_executor.parse_json_safely(resposta_texto):
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