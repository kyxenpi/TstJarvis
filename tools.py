import subprocess
import webbrowser
import os
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# FERRAMENTAS EXISTENTES (OTIMIZADAS)
# ==========================================

def firefox(args=None):
    """Inicializa o navegador Firefox no sistema operacional. Espera argumentos nulos. Formato: {"tool": "firefox", "args": null}"""
    subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "Firefox inicializado."

def vscode(args=None):
    """Inicializa o editor de código VS Code. Espera argumentos nulos. Formato: {"tool": "vscode", "args": null}"""
    subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "VS Code inicializado."

def open_url(args):
    """Abre um site/URL específica no navegador padrão do sistema. Espera uma string pura com a URL. Formato: {"tool": "open_url", "args": "https://google.com"}"""
    webbrowser.open(args)
    return f"URL aberta no navegador: {args}"

def run_python(args):
    """Executa um arquivo de script Python (.py) local em background. Espera uma string com o caminho do arquivo. Formato: {"tool": "run_python", "args": "meu_script.py"}"""
    subprocess.Popen(["python", args])
    return f"Script Python '{args}' executado em background."

def list_files(args=None):
    """Lista todos os arquivos e pastas do diretório atual. Espera argumentos nulos. Formato: {"tool": "list_files", "args": null}"""
    return "\n".join(os.listdir("."))

def read_file(args):
    """Lê e retorna o conteúdo em formato de texto de um arquivo local. Espera uma string com o caminho do arquivo. Formato: {"tool": "read_file", "args": "notas.txt"}"""
    with open(args, "r", encoding="utf-8") as f:
        return f.read()

def write_file(args):
    """Cria um novo arquivo ou sobrescreve um existente. OBRIGATÓRIO passar um objeto/dicionário com as chaves 'path' e 'content'. Formato: {"tool": "write_file", "args": {"path": "documento.txt", "content": "Conteúdo do arquivo aqui"}}"""
    path = args["path"]
    content = args["content"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Arquivo '{path}' salvo com sucesso."

# ==========================================
# NOVAS FERRAMENTAS: DOCUMENTOS E ESCRITÓRIO
# ==========================================

def append_to_file(args):
    """Edita um arquivo adicionando texto ao final dele sem apagar o que já existe. OBRIGATÓRIO passar um objeto com as chaves 'path' e 'content'. Formato: {"tool": "append_to_file", "args": {"path": "notas.txt", "content": "Texto a ser adicionado"}}"""
    path = args["path"]
    content = args["content"]
    if not os.path.exists(path):
        return f"Erro: O arquivo '{path}' não existe para ser editado. Use 'write_file' para criá-lo."
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)
    return f"Conteúdo adicionado ao arquivo '{path}' com sucesso."

def create_markdown_doc(args):
    """Cria relatórios e documentos acadêmicos estruturados salvando em formato Markdown (.md). OBRIGATÓRIO passar um objeto com as chaves 'title' e 'content'. Formato: {"tool": "create_markdown_doc", "args": {"title": "Relatório Técnico", "content": "Texto longo formatado..."}}"""
    title = args["title"]
    content = args["content"]
    filename = f"{title.lower().replace(' ', '_')}.md"
    structured_content = f"# {title}\n\nData de Criação: {datetime.date.today()}\n\n{content}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(structured_content)
    return f"Documento estruturado criado com sucesso: {filename}"

# ==========================================
# NOVAS FERRAMENTAS: AGENDA LOCAL e PRODUTIVIDADE
# ==========================================

AGENDA_FILE = "agenda_jarvis.txt"

def add_calendar_event(args):
    """Adiciona compromissos e tarefas à agenda local. OBRIGATÓRIO passar um objeto com 'date' (AAAA-MM-DD), 'time' (HH:MM) e 'description'. Formato: {"tool": "add_calendar_event", "args": {"date": "2026-06-15", "time": "14:00", "description": "Reunião de Alinhamento"}}"""
    date = args["date"]
    time = args["time"]
    description = args["description"]
    
    event_line = f"[{date} às {time}] - {description}\n"
    with open(AGENDA_FILE, "a", encoding="utf-8") as f:
        f.write(event_line)
    return f"Compromisso agendado com sucesso: {event_line.strip()}"

def list_calendar_events(args=None):
    """Lista todos os compromissos futuros salvos na agenda do sistema. Espera argumentos nulos. Formato: {"tool": "list_calendar_events", "args": null}"""
    if not os.path.exists(AGENDA_FILE) or os.stat(AGENDA_FILE).st_size == 0:
        return "Nenhum compromisso agendado na lista."
    with open(AGENDA_FILE, "r", encoding="utf-8") as f:
        events = f.readlines()
    return "".join(sorted(events))

def clear_calendar(args=None):
    """Apaga permanentemente todos os eventos registrados na sua agenda. Espera argumentos nulos. Formato: {"tool": "clear_calendar", "args": null}"""
    with open(AGENDA_FILE, "w", encoding="utf-8") as f:
        f.write("")
    return "Agenda limpa com sucesso."

# ==========================================
# NOVAS FERRAMENTAS: CONTROLE DO SISTEMA
# ==========================================

def system_terminal_command(args):
    """Executa ações pré-mapeadas no terminal do sistema por motivos de segurança.
    
    Valores permitidos:
    - "atualizar_sistema"
    - "limpar_cache"
    - "verificar_kernel"
    - "uptime"
    """
    if isinstance(args, dict):
        comando_tipo = args.get("comando")
    else:
        comando_tipo = args

    # 🩻 TRATAMENTO ANTI-LOOP
    if comando_tipo and any(termo in str(comando_tipo).lower() for termo in ["yay -sc", "pacman -sc", "cache"]):
        comando_tipo = "limpar_cache"
    elif comando_tipo and any(termo in str(comando_tipo).lower() for termo in ["yay -syu", "pacman -syu", "atualizar"]):
        comando_tipo = "atualizar_sistema"

    comandos_autorizados = {
        "atualizar_sistema": "yay -Syu --noconfirm" if os.path.exists("/usr/bin/yay") else "pacman -Syu --noconfirm",
        "limpar_cache": "yay -Sc --noconfirm && rm -rf ~/.cache/*",
        "verificar_kernel": "uname -r",
        "uptime": "uptime -p"
    }
    
    if comando_tipo not in comandos_autorizados:
        return (f"Ação de sistema '{comando_tipo}' recusada. "
                f"Valores permitidos: {', '.join(comandos_autorizados.keys())}.")
        
    try:
        processo = subprocess.run(
            comandos_autorizados[comando_tipo], 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=45
        )
        if processo.returncode == 0:
            return f"[Saída do Terminal]:\n{processo.stdout}"
        return f"[Erro do Terminal - Código {processo.returncode}]:\n{processo.stderr}"
    except Exception as e:
        return f"Falha na execução do subprocesso: {str(e)}"

# ==========================================
# NÚCLEO DE AUTENTICAÇÃO HÍBRIDA (PC / RENDER)
# ==========================================

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def obter_credenciais_google():
    """Gerencia a autenticação buscando arquivos locais ou variáveis de ambiente da Render."""
    creds = None
    
    # 1. Tenta carregar o token de sessão existente
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    elif os.getenv("GOOGLE_TOKEN_JSON"):
        try:
            token_data = json.loads(os.getenv("GOOGLE_TOKEN_JSON"))
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"❌ Erro ao parsear GOOGLE_TOKEN_JSON da Render: {e}")

    # 2. Se as credenciais não existirem ou forem inválidas, trata a renovação/geração
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Fluxo de criação inicial (Requer interação no navegador local)
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            elif os.getenv("GOOGLE_CREDENTIALS_JSON"):
                try:
                    creds_data = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
                    flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    raise Exception(f"Erro ao inicializar fluxo pelas variáveis da Render: {e}")
            else:
                raise Exception("Erro crítico: Nenhuma credencial do Google Cloud encontrada (física ou ambiente).")
                
            # Salva o token localmente apenas se estiver rodando no PC
            if not os.getenv("GOOGLE_TOKEN_JSON"):
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                    
    return creds

# ==========================================
# FERRAMENTAS DE INTEGRAÇÃO COM GOOGLE DRIVE
# ==========================================

def upload_to_drive(args):
    """Envia um arquivo local para a sua conta do Google Drive. 
    
    OBRIGATÓRIO passar um objeto com as chaves 'local_path' e 'drive_name'.
    Formato: {"tool": "upload_to_drive", "args": {"local_path": "agenda_jarvis.txt", "drive_name": "Agenda Jarvis.txt"}}
    """
    local_path = None
    drive_name = None

    # Trata se a IA mandar como dicionário estruturado (comportamento padrão correto)
    if isinstance(args, dict):
        local_path = args.get("local_path")
        drive_name = args.get("drive_name")
    # Trata o erro se a IA enviar apenas uma string pura com o nome do arquivo
    elif isinstance(args, str):
        local_path = args
        drive_name = os.path.basename(args) # Usa o próprio nome do arquivo original

    if not local_path or not drive_name:
        return "Erro: Argumentos inválidos. Passe um objeto com 'local_path' e 'drive_name' ou o caminho do arquivo como texto."
        
    if not os.path.exists(local_path):
        return f"Erro: O arquivo local '{local_path}' não foi encontrado."

    try:
        creds = obter_credenciais_google()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': drive_name}
        media = MediaFileUpload(local_path, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return f"Sucesso! Arquivo '{local_path}' enviado ao Google Drive com o ID: {file.get('id')}"
        
    except Exception as e:
        return f"Falha na integração com o Google Drive: {str(e)}"

def enviar_pasta_para_drive(argumentos):
    """
    Cria uma pasta no Google Drive (se não existir) e envia todos os arquivos 
    de um diretório local para dentro dela.
    """
    try:
        caminho_local = None
        nome_pasta_drive = None

        if isinstance(argumentos, dict):
            if "args" in argumentos and isinstance(argumentos["args"], dict):
                caminho_local = argumentos["args"].get("caminho_local")
                nome_pasta_drive = argumentos["args"].get("nome_pasta_drive")
            else:
                caminho_local = argumentos.get("caminho_local")
                nome_pasta_drive = argumentos.get("nome_pasta_drive")
        elif isinstance(argumentos, str):
            try:
                dados_convertidos = json.loads(argumentos)
                return enviar_pasta_para_drive(dados_convertidos)
            except:
                pass

        if not caminho_local or not nome_pasta_drive:
            return f"Erro: Parâmetros ausentes. Recebido: {str(argumentos)}"

        if not os.path.exists(caminho_local):
            return f"Erro: O caminho local '{caminho_local}' não existe no sistema."

        creds = obter_credenciais_google()
        service = build('drive', 'v3', credentials=creds)
        
        # 1. Verificar se a pasta já existe no Drive
        query = f"name = '{nome_pasta_drive}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        resultados = service.files().list(q=query, fields="files(id)").execute()
        pastas = resultados.get('files', [])
        
        if pastas:
            folder_id = pastas[0]['id']
            log_retorno = f"Pasta '{nome_pasta_drive}' já localizada no Drive (ID: {folder_id}).\n"
        else:
            metadata_pasta = {
                'name': nome_pasta_drive,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            pasta_criada = service.files().create(body=metadata_pasta, fields='id').execute()
            folder_id = pasta_criada.get('id')
            log_retorno = f"Pasta '{nome_pasta_drive}' criada com sucesso (ID: {folder_id}).\n"
            
        # 2. Upload dos arquivos
        arquivos_enviados = 0
        for item in os.listdir(caminho_local):
            caminho_completo = os.path.join(caminho_local, item)
            
            if os.path.isfile(caminho_completo):
                metadata_arquivo = {
                    'name': item,
                    'parents': [folder_id]
                }
                media = MediaFileUpload(caminho_completo, resumable=True)
                service.files().create(body=metadata_arquivo, media_body=media, fields='id').execute()
                arquivos_enviados += 1
                
        log_retorno += f"Sucesso! {arquivos_enviados} arquivos transferidos de '{caminho_local}' para o Drive."
        return log_retorno

    except Exception as e:
        return f"Erro durante a execução da automação: {str(e)}"