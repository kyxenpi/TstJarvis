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

from tool_registry import TOOLS 

os.environ["GROQ_API_KEY"] = os.getenv("API_KEY", "")

try:
    client = Groq()
except Exception as e:
    print(f"❌ Erro ao iniciar Groq: {e}")
    sys.exit(1)
try:
    client = Groq()
except Exception as e:
    print(f"❌ Erro ao iniciar Groq: {e}")
    sys.exit(1)

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_DO_TELEGRAM_AQUI")

tg_app = Application.builder().token(TELEGRAM_TOKEN).build()

MODELO_PRIMARIO = "llama-3.3-70b-versatile"
MODELO_SECUNDARIO = "llama-3.1-8b-instant"

lista_ferramentas_texto = ""
for nome_tool, funcao in TOOLS.items():
    descricao = funcao.__doc__.split('\n')[0].strip() if funcao.__doc__ else "Sem descrição disponível."
    lista_ferramentas_texto += f"- {nome_tool}: {descricao}\n"

SYSTEM_PROMPT = f"""Você é Jarvis, um agente operacional avançado rodando localmente na máquina do usuário.

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
    """
    Centraliza a lógica de decisão do Jarvis. 
    Recebe o texto do usuário e resolve o loop de ferramentas (Agentic Loop) na Groq.
    """
    mensagens_api = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if historico_previo:
        historico_limitado = historico_previo[-10:]
        for msg in historico_limitado:
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

        conteudo = respuesta.choices[0].message.content
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
    """Rota original para a sua interface HTML de testes locais"""
    dados = request.json
    pergunta_atual = dados.get("mensagem")
    historico_front = dados.get("historico", [])
    
    historico_adaptado = [{"type": m["type"], "text": m["text"]} for m in historico_front]
    
    _, fluxo = processar_cerebro_jarvis(pergunta_atual, historico_adaptado)
    return jsonify({"fluxo": flujo})


@app.route('/webhook', methods=['POST'])
async def telegram_webhook():
    """Recebe as mensagens do Telegram em tempo real e responde usando a Groq"""
    try:
        dados_update = request.get_json(force=True)

        update = Update.de_json(dados_update, tg_app.bot)
        
        if update.message and update.message.text:
            texto_usuario = update.message.text
            chat_id = update.message.chat_id
            
            await tg_app.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            resposta_texto, fluxo = processar_cerebro_jarvis(texto_usuario)
            
            for etapa in fluxo:
                if etapa["type"] == "tool":
                    await tg_app.bot.send_message(chat_id=chat_id, text=f"⚡ `[System]: {etapa['content']}`", parse_mode="Markdown")
            
            if not tentar_json(resposta_texto):
                await tg_app.bot.send_message(chat_id=chat_id, text=resposta_texto, parse_mode="Markdown")
                
        return 'OK', 200
    except Exception as e:
        print(f"❌ Erro na rota do Webhook: {e}")
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