import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from core.security import SecurityLevel

# Detecta se está rodando no Render ou outra nuvem
# No Render, adicione a Environment Variable: ENVIRONMENT = production
IS_CLOUD = os.getenv("ENVIRONMENT") == "production"

@dataclass
class ToolResult:
    success: bool
    output: str
    execution_time: float
    error: Optional[str] = None

class ToolRegistry:
    def __init__(self) -> None:
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, security_level: SecurityLevel = SecurityLevel.SAFE, cloud_compatible: bool = True) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.tools[name] = {
                "func": func,
                "doc": func.__doc__ or "Sem descrição disponível.",
                "security_level": security_level,
                "cloud_compatible": cloud_compatible  # Salva se a ferramenta pode rodar em nuvem
            }
            return func
        return decorator

    def get_tool_manifest(self) -> str:
        manifest = ""
        for name, info in self.tools.items():
            # Se estiver na nuvem e a ferramenta não for compatível, remove do manifesto enviado ao LLM
            if IS_CLOUD and not info["cloud_compatible"]:
                continue
                
            desc = info["doc"].split('\n')[0].strip()
            manifest += f"- {name}: {desc} [Privilégio: {info['security_level'].value}]\n"
        return manifest

registry = ToolRegistry()
tool = registry.register


@tool("list_tools", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def list_tools(args: Any = None) -> str:
    """Lista todas as ferramentas disponíveis para o usuário com descrição e nível de privilégio."""
    return registry.get_tool_manifest()