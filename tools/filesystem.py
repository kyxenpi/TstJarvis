from pathlib import Path
from typing import Any, Dict
from tools.base import tool
from core.security import SecurityLevel

@tool("list_files", security_level=SecurityLevel.SAFE)
def list_files(args: Any = None) -> str:
    """Lista todos os arquivos e pastas do diretório atual."""
    return "\n".join([str(p.name) for p in Path(".").iterdir()])

@tool("read_file", security_level=SecurityLevel.SAFE)
def read_file(args: Any) -> str:
    """Lê e retorna o conteúdo em formato de texto de um arquivo local."""
    path = Path(args if isinstance(args, str) else args.get("path", ""))
    if not path.exists():
        return f"Erro: O arquivo '{path}' não existe."
    return path.read_text(encoding="utf-8")

@tool("write_file", security_level=SecurityLevel.MEDIUM)
def write_file(args: Dict[str, Any]) -> str:
    """Cria um novo arquivo ou sobrescreve um existente. Requer 'path' e 'content'."""
    path = Path(args["path"])
    path.write_text(args["content"], encoding="utf-8")
    return f"Arquivo '{path}' salvo com sucesso."

@tool("append_to_file", security_level=SecurityLevel.MEDIUM)
def append_to_file(args: Dict[str, Any]) -> str:
    """Adiciona texto ao final de um arquivo existente sem sobrescrever."""
    path = Path(args["path"])
    if not path.exists():
        return f"Erro: O arquivo '{path}' não existe. Use 'write_file'."
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + args["content"])
    return f"Conteúdo adicionado ao arquivo '{path}'."