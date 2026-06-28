from flask import Blueprint, render_template, request, jsonify
from agent.agent import koda_agent
from agent.models import model_manager
from core.utils import get_system_telemetry

web_blueprint = Blueprint('web', __name__)

@web_blueprint.route('/')
def index():
    return render_template('index.html')

@web_blueprint.route('/chat', methods=['POST'])
def chat_web():
    dados = request.get_json() or {}
    mensagem = dados.get("mensagem", "")
    session_id = dados.get("session_id", "web_default_session")
    
    _, fluxo = koda_agent.process(session_id, mensagem)
    return jsonify({"fluxo": fluxo})

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