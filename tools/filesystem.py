import os
from pathlib import Path
from typing import Any, Dict
from tools.base import tool
from core.security import SecurityLevel

ALLOWED_DIRS = [Path("/app"), Path.home(), Path.cwd()]


def _resolve_path(user_path: str) -> Path | None:
    p = Path(user_path).resolve()
    for base in ALLOWED_DIRS:
        base_resolved = base.resolve()
        try:
            p.relative_to(base_resolved)
            return p
        except ValueError:
            continue
    return None


@tool("list_files", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def list_files(args: Any = None) -> str:
    """Lista arquivos e pastas de um diretório (padrão: atual)."""
    raw = args.get("path", ".") if isinstance(args, dict) else (args or ".")
    path = _resolve_path(raw)
    if not path:
        return f"Erro: Acesso negado a '{raw}'."
    if not path.exists():
        return f"Erro: Diretório '{path}' não existe."
    if not path.is_dir():
        return f"Erro: '{path}' não é um diretório."
    items = []
    for p in sorted(path.iterdir()):
        suffix = "/" if p.is_dir() else ""
        items.append(f"{p.name}{suffix}")
    return "\n".join(items) if items else "(vazio)"


@tool("read_file", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def read_file(args: Any) -> str:
    """Lê e retorna o conteúdo de um arquivo local."""
    raw = args if isinstance(args, str) else args.get("path", "")
    path = _resolve_path(raw)
    if not path:
        return f"Erro: Acesso negado a '{raw}'."
    if not path.exists():
        return f"Erro: '{path}' não existe."
    if not path.is_file():
        return f"Erro: '{path}' não é um arquivo."
    return path.read_text(encoding="utf-8")


@tool("write_file", security_level=SecurityLevel.MEDIUM, cloud_compatible=False)
def write_file(args: Dict[str, Any]) -> str:
    """Cria ou sobrescreve um arquivo com conteúdo. Requer 'path' e 'content'."""
    path = _resolve_path(args["path"])
    if not path:
        return f"Erro: Acesso negado a '{args['path']}'."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Arquivo '{path}' salvo."


@tool("append_to_file", security_level=SecurityLevel.MEDIUM, cloud_compatible=False)
def append_to_file(args: Dict[str, Any]) -> str:
    """Adiciona texto ao final de um arquivo existente."""
    path = _resolve_path(args["path"])
    if not path:
        return f"Erro: Acesso negado a '{args['path']}'."
    if not path.exists():
        return f"Erro: '{path}' não existe. Use write_file."
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + args["content"])
    return f"Conteúdo adicionado a '{path}'."


@tool("search_files", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def search_files(args: Any) -> str:
    """Busca arquivos por padrão glob em um diretório. Retorna até max_results (padrão 30)."""
    pattern = args if isinstance(args, str) else args.get("pattern", "*")
    raw = args.get("root", ".") if isinstance(args, dict) else "."
    root = _resolve_path(raw)
    if not root:
        return f"Erro: Acesso negado a '{raw}'."
    max_results = args.get("max_results", 30) if isinstance(args, dict) else 30

    if not root.exists():
        return f"Erro: Diretório '{root}' não existe."

    results = list(root.rglob(pattern))[:max_results]
    if not results:
        return f"Nenhum arquivo encontrado com padrão '{pattern}' em '{root}'."

    return "\n".join(str(r.relative_to(root)) for r in results)


@tool("file_info", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def file_info(args: Any) -> str:
    """Retorna informações detalhadas de um arquivo ou diretório."""
    raw = args if isinstance(args, str) else args.get("path", "")
    path = _resolve_path(raw)
    if not path:
        return f"Erro: Acesso negado a '{raw}'."
    if not path.exists():
        return f"Erro: '{path}' não existe."

    stat = path.stat()
    info = [
        f"Nome: {path.name}",
        f"Tipo: {'Diretório' if path.is_dir() else 'Arquivo'}",
        f"Tamanho: {_format_size(stat.st_size)}",
        f"Criado: {_format_time(stat.st_ctime)}",
        f"Modificado: {_format_time(stat.st_mtime)}",
    ]
    return "\n".join(info)


@tool("delete_file", security_level=SecurityLevel.DANGEROUS, cloud_compatible=False)
def delete_file(args: Any) -> str:
    """Remove um arquivo ou diretório vazio (PERIGOSO)."""
    raw = args if isinstance(args, str) else args.get("path", "")
    path = _resolve_path(raw)
    if not path:
        return f"Erro: Acesso negado a '{raw}'."
    if not path.exists():
        return f"Erro: '{path}' não existe."
    try:
        if path.is_dir():
            path.rmdir()
            return f"Diretório vazio '{path}' removido."
        path.unlink()
        return f"Arquivo '{path}' removido."
    except OSError as e:
        return f"Erro ao remover '{path}': {e}"


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_time(ts: float) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
