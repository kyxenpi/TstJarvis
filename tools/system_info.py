import platform
import subprocess
from typing import Any
from tools.base import tool
from core.security import SecurityLevel


def _run(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "N/A"


def _mem_usage() -> str:
    try:
        r = subprocess.run(
            "free -h | grep Mem",
            shell=True, capture_output=True, text=True, timeout=5
        )
        parts = r.stdout.split()
        if len(parts) >= 3:
            return f"{parts[2]}/{parts[1]} usado"
        return r.stdout.strip()
    except Exception:
        return "N/A"


def _disk_usage() -> str:
    try:
        r = subprocess.run(
            "df -h / | tail -1",
            shell=True, capture_output=True, text=True, timeout=5
        )
        parts = r.stdout.split()
        if len(parts) >= 4:
            return f"{parts[2]}/{parts[1]}"
        return r.stdout.strip()
    except Exception:
        return "N/A"


def _cpu_load() -> str:
    try:
        r = subprocess.run(
            "uptime | awk -F'load average:' '{print $2}'",
            shell=True, capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "N/A"


def _cpu_model() -> str:
    model = platform.processor()
    if model and model != "":
        return model
    try:
        r = subprocess.run(
            "lscpu | grep 'Model name' | cut -d: -f2 | xargs",
            shell=True, capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or "N/A"
    except Exception:
        return "N/A"


@tool("system_info", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def system_info(args: Any = None) -> str:
    """Retorna informações do sistema: SO, kernel, CPU, memória, disco, ZRAM."""
    info = [
        f"Sistema: {platform.system()} {platform.release()}",
        f"Hostname: {platform.node()}",
        f"Arquitetura: {platform.machine()}",
        f"Processador: {_cpu_model()}",
        f"Uptime: {_run('uptime -p')}",
        f"Kernel: {_run('uname -r')}",
        f"CPU Load: {_cpu_load()}",
        f"Memória: {_mem_usage()}",
        f"Disco (/): {_disk_usage()}",
        f"ZRAM: {_run('zramctl --noheadings --output=NAME,USED,DISKSIZE,DATA,COMPR 2>/dev/null | head -1')}",
        f"Python: {platform.python_version()}",
    ]
    return "\n".join(info)


@tool("active_processes", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def active_processes(args: Any = None) -> str:
    """Lista processos ativos ordenados por uso de memória."""
    limit = args.get("limit", 15) if isinstance(args, dict) else 15
    return _run(f"ps aux --sort=-%mem | head -{limit + 1}")
