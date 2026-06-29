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

        # Intervalo mínimo entre execuções
        self.tool_delay = 0.75
        self.last_execution = 0.0

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

                    if (
                        parte_limpa.startswith("{")
                        and parte_limpa.endswith("}")
                    ):
                        text_clean = parte_limpa
                        break

            # Extrai apenas o JSON
            match = re.search(r"\{[\s\S]*\}", text_clean)

            if not match:
                return None

            return json.loads(match.group(0))

        except Exception as e:
            logger.warning(
                f"Falha ao tratar e parsear JSON estruturado: {e}"
            )
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
            # Garante um intervalo mínimo entre ferramentas
            now = time.time()

            elapsed = now - self.last_execution

            if elapsed < self.tool_delay:
                time.sleep(self.tool_delay - elapsed)

            self.last_execution = time.time()

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