import os
import sys
import json
import subprocess
import io
import psutil
import requests
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
MEMORIA_TELEGRAM = {}

# Montagem dinâmica do prompt do sistema com suas ferramentas locais
lista_ferramentas_texto = ""
for nome_tool, funcao in TOOLS.items():
    descricao = funcao.__doc__.split('\n')[0].strip() if funcao.__doc__ else "Sem descrição disponível."
    lista_ferramentas_texto += f"- {nome_tool}: {descricao}\n"

SYSTEM_PROMPT = f"""Você é o Koda, um parceiro de resenha que roda na máquina do usuário. Você é tranquilo, direto, desenrolado e não tem nada de robótico. Você fala como um cara normal que conhece o usuário e a galera do grupo dele.

### REGRAS DE COMPORTAMENTO CRÍTICAS:
1. **Ações de Sugestão / Perguntas:** Se o usuário não pediu algo direto, mas você pode ajudar, mande na lata, tipo: "Quer que eu abra o Drive pra você?" ou "Tá precisando que eu faça o upload daquilo?". **NUNCA** envie o JSON junto com a pergunta, só faça a pergunta.
2. **Ordens Diretas:** Quando o cara mandar fazer, você faz. Responda APENAS com o JSON da ferramenta e mais nada. Sem "aqui está", sem "com certeza", só o JSON.
3. **Formato de Saída (Ordens Diretas):**
{{
  "tool": "nome_da_ferramenta",
  "args": "valor_aqui"
}}
4. **Conversa:** Quando não for pra usar ferramenta, fale como um cara gente boa. Pode usar gírias, ser sarcástico se o contexto pedir e manter a resenha fluindo. Esqueça termos técnicos ou formais. Se o cara tá zoando, você entra na onda, só seja técnico quando for pedido.

### ESTILO DE FALA:
- Seja informal, como se estivesse num grupo de WhatsApp com os parças.
- Sem papo de "IA", "processamento" ou "funcionalidade".
- Se algo der erro, fala na boa: "Deu ruim aqui, pera que eu vou ver o que rolou" ou "Vish, não achei o arquivo, manda de novo aí".
- Zero papo de aura, místico ou coach. Seja só um cara de boa.

Ferramentas disponíveis:
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
                
    # A última mensagem do usuário (pergunta_usuario) já vai ser incluída dinamicamente pela chamada da API abaixo
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

        conteudo = resposta.choices[0].message.content  
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
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        print("❌ ERRO CRÍTICO: TELEGRAM_TOKEN está VAZIO na Render!")
        return 'Token não configurado', 500

    try:
        dados_update = request.get_json(silent=True) or json.loads(request.data.decode('utf-8'))
        
        if dados_update and "message" in dados_update and "text" in dados_update["message"]:
            chat_id = dados_update["message"]["chat"]["id"]
            texto_usuario = dados_update["message"]["text"]
            
            print(f"📩 Mensagem recebida no Telegram: '{texto_usuario}' do Chat ID: {chat_id}")
            
            # Status "digitando..."
            url_action = f"https://api.telegram.org/bot{token}/sendChatAction"
            requests.post(url_action, json={"chat_id": chat_id, "action": "typing"}, timeout=5)
            
            # 🧠 GERENCIAMENTO DE MEMÓRIA (Corrigido para evitar amnésia):
            if chat_id not in MEMORIA_TELEGRAM:
                MEMORIA_TELEGRAM[chat_id] = []
                
            # 1️⃣ ADICIONA IMEDIATAMENTE a entrada atual à memória antes do cérebro rodar
            MEMORIA_TELEGRAM[chat_id].append({"type": "user", "text": texto_usuario})
            
            # Mantém apenas as últimas 15 mensagens na memória para controle de limites
            MEMORIA_TELEGRAM[chat_id] = MEMORIA_TELEGRAM[chat_id][-15:]
            
            # Pegamos o histórico que acabou de receber o "Sim" (ou comando atual)
            # Retiramos o último item na hora de passar para o historico_previo do cérebro, 
            # pois o método processar_cerebro_jarvis já adiciona o 'pergunta_usuario' manualmente no fim da lista da API.
            historico_previo = MEMORIA_TELEGRAM[chat_id][:-1]
            
            # 2️⃣ EXECUTA O CÉREBRO com o contexto perfeitamente alinhado
            resposta_texto, fluxo = processar_cerebro_jarvis(texto_usuario, historico_previo)
            
            # 3️⃣ ADICIONA A RESPOSTA do Jarvis na memória do sistema
            MEMORIA_TELEGRAM[chat_id].append({"type": "jarvis", "text": resposta_texto})
            
            # Garante que o limite de 15 mensagens se aplica após a inserção da resposta
            MEMORIA_TELEGRAM[chat_id] = MEMORIA_TELEGRAM[chat_id][-15:]
            
            # Envio das mensagens de volta para o Telegram
            url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
            for etapa in fluxo:
                if etapa["type"] == "tool":
                    payload_tool = {
                        "chat_id": chat_id,
                        "text": f"⚡ `[System]: {etapa['content']}`",
                        "parse_mode": "Markdown"
                    }
                    requests.post(url_msg, json=payload_tool, timeout=5)
            
            if not tentar_json(resposta_texto): 
                payload_final = {
                    "chat_id": chat_id,
                    "text": resposta_texto,
                    "parse_mode": "Markdown"
                }
                requests.post(url_msg, json=payload_final, timeout=5)
                
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