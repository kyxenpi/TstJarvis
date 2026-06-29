import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Dict, Any, Optional

from tools.base import registry, ToolResult
from core.logger import setup_logger

logger = setup_logger("ToolExecutor")


class ToolExecutor:
    def __init__(self) -> None:
        # Executa apenas uma ferramenta por vez
        self.pool = ThreadPoolExecutor(max_workers=1)

        # Delay antes de executar qualquer ferramenta
        self.tool_delay = 0.75

    def parse_json_safely(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            if not text or not text.strip():
                return None

            text_clean = text.strip()

            # Remove blocos markdown ```json
            if "```" in text_clean:
                partes = text_clean.split("```")
                for parte in partes:
                    parte_limpa = parte.strip()
                    if parte_limpa.startswith("json"):
                        parte_limpa = parte_limpa[4:].strip()

                    if parte_limpa.startswith("{") and parte_limpa.endswith("}"):
                        text_clean = parte_limpa
                        break

            # Extrai somente o JSON
            match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
            if match:
                text_clean = match.group(1)
            else:
                return None

            # Normaliza quebras de linha
            text_clean = re.sub(
                r'(\"[^\"]*?\")\s*',
                lambda m: m.group(1).replace("\n", "\\n"),
                text_clean,
            )

            return json.loads(text_clean)

        except Exception as e:
            logger.warning(f"Falha ao tratar e parsear JSON estruturado: {e}")
            return None

    def execute(self, tool_name: str, args: Any) -> ToolResult:
        if tool_name not in registry.tools:
            return ToolResult(
                success=False,
                output="",
                execution_time=0.0,
                error=f"Ferramenta '{tool_name}' indisponível."
            )

        info = registry.tools[tool_name]

        start_time = time.time()

        try:
            # Pequena pausa entre chamadas de ferramentas
            time.sleep(self.tool_delay)

            future = self.pool.submit(info["func"], args)

            output = future.result(timeout=40)

            elapsed = time.time() - start_time

            logger.info(
                f"Ferramenta Executada: {tool_name} em {elapsed:.2f}s"
            )

            return ToolResult(
                success=True,
                output=str(output),
                execution_time=elapsed,
            )

        except TimeoutError:
            elapsed = time.time() - start_time

            logger.error(
                f"Timeout ao executar '{tool_name}' após 40 segundos."
            )

            return ToolResult(
                success=False,
                output="",
                execution_time=elapsed,
                error="Tempo limite excedido (40s)."
            )

        except Exception as e:
            elapsed = time.time() - start_time

            logger.error(f"Erro ao executar '{tool_name}': {e}")

            return ToolResult(
                success=False,
                output="",
                execution_time=elapsed,
                error=str(e)
            )


tool_executor = ToolExecutor()