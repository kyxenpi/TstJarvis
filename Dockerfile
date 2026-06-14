FROM python:3.11-slim

# Instala dependências do sistema que o psutil ou comandos locais possam precisar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Comando que liga o Flask em modo ASGI/Async usando Gunicorn + Uvicorn
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:5000", "wsgi:app"]