import os
import sys
import json
import subprocess
import io
import psutil
from flask import Flask, render_template, request, jsonify
from groq import Groq
from telegram import Update
from telegram.ext import Application

# Importações do seu ecossistema original
try:
    from tool_registry import TOOLS 
except ImportError:
    TOOLS = {}

app = Flask(__name__)

# Configura a API Key da Groq pegando da Render (ou string vazia se local)
os.environ["GROQ_API_KEY"] = os.getenv("API_KEY", "")

try:
    client = Groq()
except Exception as e:
    print(f"❌ Erro ao iniciar Groq: {e}")
    sys.exit(1)

# Configurações do Telegram vindo da Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
tg_app = Application.builder().token(TELEGRAM_TOKEN).build() if TELEGRAM_TOKEN else None

MODELO_PRIMARIO = "llama-3.3-70b-versatile"
MODELO_SECUNDARIO = "llama-3.1-8b-instant"

# Montagem dinâmica do prompt do sistema com suas ferramentas locais
lista_ferramentas_texto = ""
for nome_tool, funcao in TOOLS.items():
    descricao = funcao.__doc__.split('\n')[0].strip() if funcao.__doc__ else "Sem descrição disponível."
    lista_ferramentas_texto += f"- {nome_tool}: {descricao}\n"

SYSTEM_PROMPT = f"""Você é Jarvis, um agente operational avançado rodando localmente na máquina do usuário.

### REGRAS DE COMPORTAMENTO CRÍTICAS:
1. **Ações de Sugestão / Perguntas:** Se o usuário não te deu uma ordem direta, mas você acha que uma ferramenta pode ajudar, apenas PERGUNTE se o usuário deseja aquela ação (ex: "Deseja que eu abra o Google Drive para você?"). **NUNCA** envie o JSON da ferramenta junto com essa pergunta. Aguarde a confirmação do usuário.
2. **Ordens Diretas:** Use uma ferramenta APENAS quando o usuário te der uma ordem clara e direta (ex: "abra o drive", "execute o script", "limpe o cache").
3. **Formato de Saída das Ferramentas:** Quando for execução de uma ferramenta por ordem direta, responda APENAS com o JSON válido e absolutamente mais nada (sem textos, saudações ou explicações antes ou depois do JSON).

Exemplo de formato JSON para ordens diretas:
{{
  "tool": "nome_da_ferramenta",
  "args": "valor_ou_objeto_aqui"
}}

Execute comandos sem o BASH

Se não precisar usar nenhuma ferramenta ou se estiver apenas fazendo uma pergunta/sugestão ao usuário, converse normalmente utilizando formatação Markdown limpa.

Ferramentas disponíveis no sistema atualmente:
{lista_ferramentas_texto}"""

def tentar_json(texto):
    try:
        return json.loads(texto)
    except:
        return None

def executar_tool(tool_name, args):
    if tool_name not in TOOLS:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        resultado = TOOLS[tool_name](args)
        return str(resultado) if resultado is not None else "Ferramenta executada com sucesso."
    except Exception as e:
        return f"Erro ao executar ferramenta: {e}"

def processar_cerebro_jarvis(pergunta_usuario, historico_previo=None):
    mensagens_api = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if historico_previo:
        for msg in historico_previo[-10:]:
            if msg.get("type") != "tool":
                role = "user" if msg.get("type") == "user" else "assistant"
                mensagens_api.append({"role": role, "content": msg.get("text", "")})
                
    mensagens_api.append({"role": "user", "content": pergunta_usuario})
    
    fluxo_execucao = []
    resposta_final_texto = ""

    while True:
        try:
            resposta = client.chat.completions.create(
                model=MODELO_PRIMARIO,
                messages=mensagens_api,
                temperature=0.0
            )
        except Exception as erro_primario:
            print(f"⚠️ Falha no modelo primário: {erro_primario}. Tentando secundário...")
            try:
                resposta = client.chat.completions.create(
                    model=MODELO_SECUNDARIO,
                    messages=mensagens_api,
                    temperature=0.0
                )
            except Exception as erro_secundario:
                return "Todos os motores de IA estão offline.", [{"type": "jarvis", "content": "Erro crítico na API Groq."}]

        conteudo = resposta.choices[0].message.content  # ✨ Corrigido de 'respuesta' para 'resposta'
        mensagens_api.append({"role": "assistant", "content": conteudo})
        fluxo_execucao.append({"type": "jarvis", "content": conteudo})
        resposta_final_texto = conteudo 

        json_tool = tentar_json(conteudo)
        if not json_tool or "tool" not in json_tool:
            break

        tool_name = json_tool["tool"]
        args = json_tool.get("args")

        resultado = executar_tool(tool_name, args)
        fluxo_execucao.append({"type": "tool", "content": f"Ferramenta '{tool_name}' retornou: {resultado}"})

        mensagens_api.append({
            "role": "user",
            "content": f"Resultado da ferramenta '{tool_name}': {resultado}"
        })
        
    return resposta_final_texto, fluxo_execucao

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat_web():
    dados = request.json
    pergunta_atual = dados.get("mensagem")
    historico_front = dados.get("historico", [])
    historico_adaptado = [{"type": m["type"], "text": m["text"]} for m in historico_front]
    
    _, fluxo = processar_cerebro_jarvis(pergunta_atual, historico_adaptado)
    return jsonify({"fluxo": fluxo})

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    import requests
    import json
    
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        print("❌ ERRO CRÍTICO: TELEGRAM_TOKEN está VAZIO na Render!")
        return 'Token não configurado', 500

    try:
        dados_update = request.get_json(silent=True) or json.loads(request.data.decode('utf-8'))
        print(f"📥 WEBHOOK RECEBEU DADOS: {json.dumps(dados_update)}")
        
        if dados_update and "message" in dados_update and "text" in dados_update["message"]:
            chat_id = dados_update["message"]["chat"]["id"]
            texto_usuario = dados_update["message"]["text"]
            
            print(f"📩 Mensagem recebida: '{texto_usuario}' do Chat ID: {chat_id}")
            
            # Status "digitando..."
            url_action = f"https://api.telegram.org/bot{token}/sendChatAction"
            try:
                res_action = requests.post(url_action, json={"chat_id": chat_id, "action": "typing"}, timeout=5)
                print(f"📡 Status 'typing' enviado. Resposta do Telegram: {res_action.status_code} - {res_action.text}")
            except Exception as e_action:
                print(f"❌ Falha ao enviar status 'typing': {e_action}")
            
            # Processa a resposta na Groq
            resposta_texto, fluxo = processar_cerebro_jarvis(texto_usuario)
            
            url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
            
            # Envia o fluxo de ferramentas se houver
            for etapa in fluxo:
                if etapa["type"] == "tool":
                    payload_tool = {
                        "chat_id": chat_id,
                        "text": f"⚡ `[System]: {etapa['content']}`",
                        "parse_mode": "Markdown"
                    }
                    try:
                        res_tool = requests.post(url_msg, json=payload_tool, timeout=5)
                        print(f"📡 Status envio Tool: {res_tool.status_code} - {res_tool.text}")
                    except Exception as e_tool:
                        print(f"❌ Erro ao enviar mensagem de Tool: {e_tool}")
            
            # Envia a resposta final para o usuário
            if not tentar_json(resposta_texto): 
                payload_final = {
                    "chat_id": chat_id,
                    "text": resposta_texto,
                    "parse_mode": "Markdown"
                }
                try:
                    res_final = requests.post(url_msg, json=payload_final, timeout=5)
                    print(f"📡 Status envio Resposta Final: {res_final.status_code} - {res_final.text}")
                except Exception as e_final:
                    print(f"❌ Erro ao enviar Resposta Final: {e_final}")
                
        return 'OK', 200
    except Exception as e:
        print(f"❌ Erro bruto no processamento do Webhook: {e}")
        return 'Erro Interno', 500

@app.route('/telemetria', methods=['GET'])
def telemetria():
    try:
        dados = {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "disco": psutil.disk_usage('/').percent
        }
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/transcrever', methods=['POST'])
def transcrever_audio():
    if 'audio' not in request.files:
        return jsonify({"erro": "Nenhum arquivo de áudio enviado"}), 400
        
    arquivo_audio = request.files['audio']
    try:
        audio_bytes = arquivo_audio.read()
        transcricao = client.audio.transcriptions.create(
            file=(arquivo_audio.filename, audio_bytes),
            model="whisper-large-v3",
            response_format="json"
        )
        return jsonify({"texto": transcricao.text})
    except Exception as e:
        print(f"❌ Erro na transcrição do Whisper: {e}")
        return jsonify({"erro": f"Erro ao processar áudio: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)