import time
import re
import json
import ast
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Dict, Any, Optional

from tools.base import registry, ToolResult
from core.logger import setup_logger

logger = setup_logger("ToolExecutor")


class ToolExecutor:
    def __init__(self) -> None:
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.tool_delay = 0.5
        self.last_execution = 0.0
        self.default_timeout = 40.0
        self.timeout_per_tool = {
            "web_search": 20.0,
            "google_docs": 25.0,
            "upload_to_drive": 30.0,
            "system_terminal_command": 45.0,
        }

    def parse_json_safely(self, text: str) -> Optional[Dict[str, Any]]:
        if not text or not text.strip():
            return None

        text_clean = text.strip()

        strategies = [
            self._extract_json_block,
            self._extract_json_regex,
            self._parse_ast_dict,
        ]

        for strategy in strategies:
            result = strategy(text_clean)
            if result is not None:
                return result

        return None

    def _extract_json_block(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            if "```" in text:
                partes = text.split("```")
                for parte in partes:
                    p = parte.strip()
                    if p.startswith("json"):
                        p = p[4:].strip()
                    if p.startswith("{") and p.endswith("}"):
                        return json.loads(p)
            else:
                if text.startswith("{") and text.endswith("}"):
                    return json.loads(text)
        except Exception:
            pass
        return None

    def _extract_json_regex(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                candidate = match.group(0)
                return json.loads(candidate)
        except Exception:
            pass
        return None

    def _parse_ast_dict(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r"```(\w+)?", "", text).strip()
            parsed = ast.literal_eval(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return None

    def extract_tool_calls(self, text: str) -> Optional[Dict[str, Any]]:
        parsed = self.parse_json_safely(text)
        if parsed and "tool_calls" in parsed:
            return parsed
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
        timeout = self.timeout_per_tool.get(tool_name, self.default_timeout)

        try:
            now = time.time()
            elapsed = now - self.last_execution
            if elapsed < self.tool_delay:
                time.sleep(self.tool_delay - elapsed)
            self.last_execution = time.time()

            future = self.pool.submit(info["func"], args)
            output = future.result(timeout=timeout)

            elapsed = time.time() - start_time
            logger.info(f"Ferramenta Executada: {tool_name} em {elapsed:.2f}s")

            return ToolResult(
                success=True,
                output=str(output),
                execution_time=elapsed,
            )

        except TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout ao executar '{tool_name}' após {timeout}s.")

            return ToolResult(
                success=False,
                output="",
                execution_time=elapsed,
                error=f"Tempo limite excedido ({timeout}s)."
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
