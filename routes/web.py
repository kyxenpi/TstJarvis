import os
import uuid
import json
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, Response
from agent.agent import koda_agent
from agent.models import model_manager
from core.utils import get_system_telemetry
from agent.image_process import read_image 

web_blueprint = Blueprint('web', __name__)


@web_blueprint.route('/')
def index():
    return render_template('index.html')


def _process_image(mensagem: str) -> str:
    if 'imagem' not in request.files:
        return mensagem
    arquivo_img = request.files['imagem']
    if not arquivo_img or not arquivo_img.filename:
        return mensagem

    ext = Path(arquivo_img.filename).suffix if '.' in arquivo_img.filename else ''
    temp_filename = f"/tmp/koda_web_{uuid.uuid4().hex}{ext}"
    try:
        arquivo_img.save(temp_filename)
        resultado_ocr = read_image(temp_filename)
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        if resultado_ocr.get("success") and resultado_ocr.get("output"):
            texto_extraido = resultado_ocr["output"]
            prompt_final = f"[Texto extraído da imagem enviada pelo usuário]:\n{texto_extraido}"
            if mensagem:
                prompt_final += f"\n\n[Comando/Mensagem do usuário]: {mensagem}"
            return prompt_final
        else:
            if mensagem:
                return f"[Sistema: Uma imagem foi anexada, mas nenhum texto foi extraído dela]. Comando do usuário: {mensagem}"
            return "[Sistema: O usuário enviou uma imagem vazia ou sem texto legível]."
    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise


@web_blueprint.route('/chat', methods=['POST'])
def chat_web():
    if request.is_json:
        dados = request.get_json() or {}
        mensagem = dados.get("mensagem", "")
        session_id = dados.get("session_id", "web_default_session")
    else:
        mensagem = request.form.get("mensagem", "")
        session_id = request.form.get("session_id", "web_default_session")

    try:
        mensagem = _process_image(mensagem)
    except Exception as e:
        return jsonify({"erro": f"Erro ao processar imagem: {str(e)}"}), 500

    if not mensagem:
        return jsonify({"erro": "Nenhuma mensagem ou imagem foi enviada"}), 400

    resposta_texto, fluxo = koda_agent.process(session_id, mensagem)
    return jsonify({"fluxo": fluxo, "resposta": resposta_texto})


@web_blueprint.route('/chat/stream', methods=['POST'])
def chat_stream():
    if request.is_json:
        dados = request.get_json() or {}
        mensagem = dados.get("mensagem", "")
        session_id = dados.get("session_id", "web_default_session")
    else:
        mensagem = request.form.get("mensagem", "")
        session_id = request.form.get("session_id", "web_default_session")

    try:
        mensagem = _process_image(mensagem)
    except Exception as e:
        def err():
            yield f"data: {json.dumps({'type': 'error', 'content': f'Erro ao processar imagem: {str(e)}'})}\n\n"
        return Response(err(), mimetype='text/event-stream')

    if not mensagem:
        def empty():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Nenhuma mensagem ou imagem foi enviada'})}\n\n"
        return Response(empty(), mimetype='text/event-stream')

    def generate():
        for event in koda_agent.stream_process(session_id, mensagem):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


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
