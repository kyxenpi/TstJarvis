import os
from flask import Blueprint, render_template, request, jsonify
from agent.agent import koda_agent
from agent.models import model_manager
from core.utils import get_system_telemetry
# Importa a sua função de processamento de imagem
from agent.image_process import read_image 

web_blueprint = Blueprint('web', __name__)

@web_blueprint.route('/')
def index():
    return render_template('index.html')

@web_blueprint.route('/chat', methods=['POST'])
def chat_web():
    # Como agora aceitamos arquivos, os dados textuais virão via request.form
    # mas mantemos o fallback para get_json() caso o front-end envie texto puro antiga
    if request.is_json:
        dados = request.get_json() or {}
        mensagem = dados.get("mensagem", "")
        session_id = dados.get("session_id", "web_default_session")
    else:
        mensagem = request.form.get("mensagem", "")
        session_id = request.form.get("session_id", "web_default_session")

    # --- VERIFICA SE FOI ENVIADA UMA IMAGEM ---
    if 'imagem' in request.files:
        arquivo_img = request.files['imagem']
        
        if arquivo_img and arquivo_img.filename != '':
            print(f"📸 [WEB CHAT]: Imagem recebida: {arquivo_img.filename}. Processando OCR...")
            
            temp_filename = f"temp_web_{arquivo_img.filename}"
            try:
                # Salva a imagem temporariamente no disco
                arquivo_img.save(temp_filename)
                
                # Executa o seu EasyOCR
                resultado_ocr = read_image(temp_filename)
                
                # Remove o arquivo temporário imediatamente
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                
                if resultado_ocr.get("success") and resultado_ocr.get("output"):
                    texto_extraido = resultado_ocr["output"]
                    print(f"📝 [WEB OCR SUCESSO]: Texto extraído: '{texto_extraido}'")
                    
                    # Formata o prompt mesclando o texto da imagem com o texto que o usuário digitou no chat
                    prompt_final = f"[Texto extraído da imagem enviada pelo usuário]:\n{texto_extraido}"
                    if mensagem:
                        prompt_final += f"\n\n[Comando/Mensagem do usuário]: {mensagem}"
                    mensagem = prompt_final
                else:
                    if mensagem:
                        mensagem = f"[Sistema: Uma imagem foi anexada, mas nenhum texto foi extraído dela]. Comando do usuário: {mensagem}"
                    else:
                        mensagem = "[Sistema: O usuário enviou uma imagem vazia ou sem texto legível]."
                        
            except Exception as e:
                print(f"❌ [WEB OCR ERROR]: Falha ao processar imagem da web: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                return jsonify({"erro": f"Erro ao processar imagem: {str(e)}"}), 500

    # Se não houver mensagem nem texto extraído de imagem, cancela
    if not mensagem:
        return jsonify({"erro": "Nenhuma mensagem ou imagem foi enviada"}), 400

    resposta_texto, fluxo = koda_agent.process(session_id, mensagem)
    return jsonify({"fluxo": fluxo, "resposta": resposta_texto})

@web_blueprint.route('/telemetria', methods=['GET'])
def telemetria():
    return jsonify(get_system_telemetry())

@web_blueprint.route('/transcrever', methods=['POST'])
def transcrever_audio():
    if 'audio' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
    arquivo = request.files['audio']
    try:
        texto = model_manager.transcrever_audio(arquivo.filename, arquivo.read())
        return jsonify({"texto": texto})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500