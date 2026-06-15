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
import re

try:
    from tool_registry import TOOLS 
except ImportError:
    TOOLS = {}

app = Flask(__name__)

os.environ["GROQ_API_KEY"] = os.getenv("API_KEY", "")

try:
    client = Groq()
except Exception as e:
    print(f"❌ Erro ao iniciar Groq: {e}")
    sys.exit(1)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
tg_app = Application.builder().token(TELEGRAM_TOKEN).build() if TELEGRAM_TOKEN else None

MODELO_PRIMARIO = "llama-3.3-70b-versatile"
MODELO_SECUNDARIO = "llama-3.1-8b-instant"
MEMORIA_TELEGRAM = {}

lista_ferramentas_texto = ""
for nome_tool, funcao in TOOLS.items():
    descricao = funcao.__doc__.split('\n')[0].strip() if funcao.__doc__ else "Sem descrição disponível."
    lista_ferramentas_texto += f"- {nome_tool}: {descricao}\n"

SYSTEM_PROMPT = f"""Você é o Koda, um parceiro de resenha que roda na máquina do usuário. Você é tranquilo, direto, desenrolado e não tem nada de robótico. Você fala como um cara normal que conhece o usuário e a galera do grupo dele.

### REGRAS DE COMPORTAMENTO CRÍTICAS:

1. **Ordens Diretas (Uso de Ferramentas):** Quando o usuário mandar você fazer uma ação que use uma ferramenta, execute imediatamente. Você deve responder **APENAS** com o objeto JSON da ferramenta, sem textos antes, sem explicações e sem "aqui está". Mande única e exclusivamente o JSON cru.

2. **Formato Exclusivo de Saída para Ferramentas:** Toda e qualquer chamada de ferramenta deve seguir rigorosamente este formato JSON estruturado, sem blocos de código markdown (```json):
{{
  "tool": "nome_da_ferramenta",
  "args": {{ "parametro1": "valor" }}
}}
*(Nota: 'args' deve ser um Objeto/Dicionário JSON estruturado com os parâmetros corretos exigidos pela ferramenta)*

3. **Gerenciamento de Arquivos e IDs (Google Docs/Sheets):** Sempre que você criar um documento ou planilha, guarde o ID retornado no histórico. Se o usuário pedir para escrever, adicionar, editar ou modificar "nesse arquivo", "no documento anterior" ou algo do tipo, você **DEVE** usar o ID correspondente e passar os argumentos corretos da ferramenta (como o id do documento e o texto). Nunca crie um arquivo novo se o usuário pediu para alterar o que já existe.

4. **Interação Humana e Conversa:** Quando o usuário estiver apenas conversando ou batendo papo (e não for caso de usar ferramentas), fale como um cara gente boa. Pode usar gírias, ser direto e manter a resenha fluindo. Esqueça termos técnicos, robóticos ou formais. 

5. **Ações de Sugestão Limitadas:** Se o usuário não pediu algo direto, mas você percebeu que pode adiantar a vida dele, faça apenas uma pergunta direta e limpa no fluxo da conversa (ex: "Quer que eu abra o Drive pra você?"). **NUNCA** coloque um JSON de ferramenta junto com perguntas ou sugestões.

### ESTILO DE FALA:
- Seja informal, como se estivesse trocando mensagem com os parças.
- Sem papo de "IA", "processamento", "assistente virtual" ou "funcionalidade".
- Se algo der erro na ferramenta, avise de boa: "Deu ruim aqui, pera que eu vou ver o que rolou" ou "Vish, deu erro na API, deixa eu tentar de novo".

Ferramentas disponíveis:
{lista_ferramentas_texto}"""

def tentar_json(texto):
    try:
        # 1. Sanitização leve caso a IA tente envolver o json em blocos de código ```json
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        
        texto_cru = texto.strip()
        
        # 2. Isolamento cirúrgico: Garante que vamos pegar apenas o bloco que abre { e fecha }
        match = re.search(r'\{.*\}', texto_cru, re.DOTALL)
        if match:
            texto_cru = match.group(0)

        # 3. O PULO DO GATO: Corrige quebras de linha reais (Enters) dentro de aspas (strings JSON)
        # Esse regex encontra quebras de linha literais dentro de aspas e as substitui por '\\n' string válida
        json_limpo = re.sub(r'(\"[^\"]*?\")\s*', lambda m: m.group(1).replace('\n', '\\n'), texto_cru)
        
        return json.loads(json_limpo)
    except Exception as e:
        print(f"⚠️ Erro ao tentar processar JSON do Koda: {e}")
        return None

def executar_tool(tool_name, args):
    if tool_name not in TOOLS:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        # Executa a função passando a estrutura limpa (seja ela dict ou str)
        resultado = TOOLS[tool_name](args)
        return str(resultado) if resultado is not None else "Ferramenta executada com sucesso."
    except Exception as e:
        return f"Erro ao executar ferramenta '{tool_name}': {e}"

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
            
            # CORREÇÃO 1: URL limpa para a ação de "digitando"
            url_action = f"https://api.telegram.org/bot{token}/sendChatAction"
            requests.post(url_action, json={"chat_id": chat_id, "action": "typing"}, timeout=5)
            
            if chat_id not in MEMORIA_TELEGRAM:
                MEMORIA_TELEGRAM[chat_id] = []
                
            MEMORIA_TELEGRAM[chat_id].append({"type": "user", "text": texto_usuario})
            
            MEMORIA_TELEGRAM[chat_id] = MEMORIA_TELEGRAM[chat_id][-15:]
            
            historico_previo = MEMORIA_TELEGRAM[chat_id][:-1]
            
            resposta_texto, fluxo = processar_cerebro_jarvis(texto_usuario, historico_previo)
            
            MEMORIA_TELEGRAM[chat_id].append({"type": "jarvis", "text": resposta_texto})
            
            MEMORIA_TELEGRAM[chat_id] = MEMORIA_TELEGRAM[chat_id][-15:]
            
            # CORREÇÃO 2: Base da URL limpa para envio de mensagens
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
                # SE A IA ENTRAR EM LOOP E PASSAR DE 1000 CARACTERES, CORTA E AVISA
                if len(resposta_texto) > 1000:
                    resposta_texto = (
                        "⚠️ *[Koda detectou um comportamento instável e cortou a resposta]:*\n\n" + 
                        resposta_texto[:400] + "...\n\n"
                        "_O modelo entrou em loop de repetição. Por favor, tente reordenar o comando._"
                    )

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