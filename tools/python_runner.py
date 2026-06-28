import subprocess
from pathlib import Path
from typing import Any
from tools.base import tool
from core.security import SecurityLevel

@tool("run_python", security_level=SecurityLevel.MEDIUM)
def run_python(args: Any) -> str:
    """Executa um script Python (.py) local em background."""
    path = args if isinstance(args, str) else args.get("path", "")
    if not Path(path).exists():
        return f"Erro: O arquivo '{path}' não existe."
    subprocess.Popen(["python", path])
    return f"Script Python '{path}' executado em background."