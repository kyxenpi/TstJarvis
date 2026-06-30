import subprocess
import webbrowser
from urllib.parse import urlparse
from tools.base import tool
from core.security import SecurityLevel


def _valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


@tool("firefox", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def open_firefox(args: any = None) -> str:
    """Abre o navegador Firefox."""
    subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "Firefox aberto."


@tool("vscode", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def open_vscode(args: any = None) -> str:
    """Abre o VS Code."""
    subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "VS Code aberto."


@tool("open_url", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def open_url(args: any) -> str:
    """Abre uma URL no navegador padrão com validação automática de esquema."""
    url = args if isinstance(args, str) else args.get("url", "")
    if not _valid_url(url):
        if " " not in url and "." in url:
            url = f"https://{url}"
        else:
            return f"URL inválida: {url}"
    if not _valid_url(url):
        return f"URL inválida: {url}"
    webbrowser.open(url)
    return f"Abrindo: {url}"


@tool("search_web", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def search_web(args: any) -> str:
    """Abre o Google Search no navegador com a query fornecida."""
    query = args if isinstance(args, str) else args.get("query", "")
    if not query:
        return "Nada a pesquisar."
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    return f"Pesquisando: {query}"
