import subprocess
import webbrowser
from tools.base import tool
from core.security import SecurityLevel

@tool("firefox", security_level=SecurityLevel.SAFE)
def firefox(args: any = None) -> str:
    """Inicializa o navegador Firefox no sistema operacional. Espera argumentos nulos."""
    subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "Firefox inicializado."

@tool("vscode", security_level=SecurityLevel.SAFE)
def vscode(args: any = None) -> str:
    """Inicializa o editor de código VS Code. Espera argumentos nulos."""
    subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "VS Code inicializado."

@tool("open_url", security_level=SecurityLevel.SAFE)
def open_url(args: any) -> str:
    """Abre uma URL específica no navegador padrão do sistema."""
    url = args if isinstance(args, str) else args.get("url", "")
    webbrowser.open(url)
    return f"URL aberta no navegador: {url}"