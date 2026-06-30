import subprocess
from pathlib import Path
from typing import Any, Dict
from tools.base import tool
from core.security import SecurityLevel

AUTHORIZED_COMMANDS = {
    "atualizar_sistema": ("yay -Syu --noconfirm" if Path("/usr/bin/yay").exists() else "pacman -Syu --noconfirm"),
    "limpar_cache": "yay -Sc --noconfirm && rm -rf ~/.cache/*",
    "verificar_kernel": "uname -r",
    "uptime": "uptime -p",
    "disk_usage": "df -h / /home",
    "memory_info": "free -h",
    "process_count": "ps aux --no-headers | wc -l",
    "wifi_status": "iwconfig 2>/dev/null || nmcli device wifi list 2>/dev/null || echo 'Sem info WiFi disponível'",
}

ALIAS_MAP = {
    "atualizar": "atualizar_sistema",
    "update": "atualizar_sistema",
    "upgrade": "atualizar_sistema",
    "cache": "limpar_cache",
    "clean": "limpar_cache",
    "kernel": "verificar_kernel",
    "disco": "disk_usage",
    "disk": "disk_usage",
    "ram": "memory_info",
    "memoria": "memory_info",
    "memory": "memory_info",
    "processos": "process_count",
    "process": "process_count",
    "wifi": "wifi_status",
    "rede": "wifi_status",
}


@tool("system_terminal_command", security_level=SecurityLevel.DANGEROUS, cloud_compatible=False)
def system_terminal_command(args: Any) -> str:
    """Executa comandos pré-mapeados no terminal: atualizar_sistema, limpar_cache, disk_usage, memory_info, etc."""
    cmd_type = args.get("comando") if isinstance(args, dict) else args
    if not cmd_type or not isinstance(cmd_type, str):
        return "Erro: parâmetro 'comando' é obrigatório."

    cmd_lower = cmd_type.strip().lower()

    resolved = ALIAS_MAP.get(cmd_lower, cmd_lower)

    if resolved not in AUTHORIZED_COMMANDS:
        return f"Ação recusada. Disponíveis: {', '.join(sorted(AUTHORIZED_COMMANDS.keys()))}."

    try:
        proc = subprocess.run(
            AUTHORIZED_COMMANDS[resolved],
            shell=True,
            capture_output=True,
            text=True,
            timeout=45
        )
        output = proc.stdout or proc.stderr or "(sem saída)"
        return output.strip()
    except subprocess.TimeoutExpired:
        return "Comando excedeu o tempo limite (45s)."
    except Exception as e:
        return f"Erro no subprocesso: {str(e)}"
