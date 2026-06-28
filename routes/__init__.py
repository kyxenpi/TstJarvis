# routes/__init__.py
from routes.telegram import telegram_blueprint
from routes.web import web_blueprint  # Se o web.py também for um Blueprint