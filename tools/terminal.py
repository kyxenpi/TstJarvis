import subprocess
from pathlib import Path
from typing import Any, Dict
from tools.base import tool
from core.security import SecurityLevel

@tool("system_terminal_command", security_level=SecurityLevel.DANGEROUS)
def system_terminal_command(args: Any) -> str:
    """Executa ações pré-mapeadas críticas no terminal por segurança."""
    cmd_type = args.get("comando") if isinstance(args, dict) else args
    
    if cmd_type and any(t in str(cmd_type).lower() for t in ["yay -sc", "pacman -sc", "cache"]):
        cmd_type = "limpar_cache"
    elif cmd_type and any(t in str(cmd_type).lower() for t in ["yay -syu", "pacman -syu", "atualizar"]):
        cmd_type = "atualizar_sistema"

    authorized = {
        "atualizar_sistema": "yay -Syu --noconfirm" if Path("/usr/bin/yay").exists() else "pacman -Syu --noconfirm",
        "limpar_cache": "yay -Sc --noconfirm && rm -rf ~/.cache/*",
        "verificar_kernel": "uname -r",
        "uptime": "uptime -p"
    }
    
    if cmd_type not in authorized:
        return f"Ação recusada. Permitidos: {', '.join(authorized.keys())}."
        
    try:
        proc = subprocess.run(authorized[cmd_type], shell=True, capture_output=True, text=True, timeout=45)
        return f"[Saída]:\n{proc.stdout}" if proc.returncode == 0 else f"[Erro]:\n{proc.stderr}"
    except Exception as e:
        return f"Falha catastrófica no subprocesso: {str(e)}"