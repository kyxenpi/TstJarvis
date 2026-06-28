from flask import Flask
from routes.web import web_blueprint
from routes.telegram import telegram_blueprint
from core.logger import setup_logger

logger = setup_logger("AppInit")

app = Flask(__name__)

# Acoplamento dos Blueprints modulares
app.register_blueprint(web_blueprint)
app.register_blueprint(telegram_blueprint)

if __name__ == '__main__':
    logger.info("Iniciando Koda Agent Core Server na porta 5000...")
    app.run(debug=True, port=5000)