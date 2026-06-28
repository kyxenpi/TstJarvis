import psutil
from typing import Dict, Any

def get_system_telemetry() -> Dict[str, Any]:
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "disco": psutil.disk_usage('/').percent
    }