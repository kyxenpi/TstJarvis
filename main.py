import os
from flask import Flask, jsonify
from flask_cors import CORS
from routes.web import web_blueprint
from routes.telegram import telegram_blueprint
from core.logger import setup_logger

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = setup_logger("AppInit")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)


@app.route('/health')
def health():
    return jsonify({"status": "ok"})


app.register_blueprint(web_blueprint)
app.register_blueprint(telegram_blueprint)

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    logger.info(f"Iniciando Koda Agent Core Server na porta {port}...")
    app.run(debug=True, host="0.0.0.0", port=port)