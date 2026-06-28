import time
import re
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from tools.base import registry, ToolResult
from core.logger import setup_logger

logger = setup_logger("ToolExecutor")

class ToolExecutor:
    def __init__(self) -> None:
        self.pool = ThreadPoolExecutor(max_workers=4)

    def parse_json_safely(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            if not text or not text.strip():
                return None
                
            text_clean = text.strip()
            
            # Remove blocos de marcação markdown se o modelo insistir em usar
            if "```" in text_clean:
                partes = text_clean.split("```")
                for parte in partes:
                    parte_limpa = parte.strip()
                    if parte_limpa.startswith("json"):
                        parte_limpa = parte_limpa[4:].strip()
                    if parte_limpa.startswith("{") and parte_limpa.endswith("}"):
                        text_clean = parte_limpa
                        break

            # Garante a extração isolando estritamente do primeiro '{' até o último '}'
            # Isso resolve o erro de "Extra data" (ignora textos após o fechamento do JSON)
            match = re.search(r'(\{.*\})', text_clean, re.DOTALL)
            if match:
                text_clean = match.group(1)
            else:
                # Se não tem chaves, é apenas texto puro de conversa de boa
                return None

            # Normaliza quebras de linha internas em strings textuais para evitar quebra de parse
            text_clean = re.sub(r'(\"[^\"]*?\")\s*', lambda m: m.group(1).replace('\n', '\\n'), text_clean)
            
            return json.loads(text_clean)
        except Exception as e:
            logger.warning(f"Falha ao tratar e parsear JSON estruturado: {e}")
            return None

    def execute(self, tool_name: str, args: Any) -> ToolResult:
        if tool_name not in registry.tools:
            return ToolResult(success=False, output="", execution_time=0.0, error=f"Ferramenta '{tool_name}' indisponível.")
            
        info = registry.tools[tool_name]
        start_time = time.time()
        
        try:
            # Submete a tarefa ao ThreadPoolExecutor para isolamento assíncrono
            future = self.pool.submit(info["func"], args)
            output = future.result(timeout=40)
            elapsed = time.time() - start_time
            
            logger.info(f"Ferramenta Executada: {tool_name} em {elapsed:.2f}s")
            return ToolResult(success=True, output=str(output), execution_time=elapsed)
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Erro ao executar {tool_name}: {e}")
            return ToolResult(success=False, output="", execution_time=elapsed, error=str(e))

tool_executor = ToolExecutor()