import json
import ast
from typing import Any, Dict, Optional
import requests as http_requests

from tools.base import tool
from core.security import SecurityLevel
from core.logger import setup_logger

logger = setup_logger("WebAPI")


def _parse_args(args: Any) -> Dict[str, Any]:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        s = args.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            try:
                p = ast.literal_eval(s)
                if isinstance(p, dict):
                    return p
            except Exception:
                pass
    return {}


@tool("web_api", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def web_api(args: Any) -> Dict[str, Any]:
    """Faz requisições HTTP para qualquer API REST.
    Parâmetros:
    - 'url' (obrigatório): endpoint completo
    - 'method': GET (padrão), POST, PUT, PATCH, DELETE
    - 'headers': dict opcional de cabeçalhos
    - 'body': dict opcional enviado como JSON (para POST/PUT/PATCH)
    - 'params': dict opcional de query parameters
    - 'timeout': segundos (padrão 15)

    Exemplos:
    - GET: {"url": "https://api.github.com/users/octocat"}
    - POST: {"url": "https://api.exemplo.com/data", "method": "POST", "body": {"nome": "Joao"}}
    - Com token: {"url": "https://api.github.com/user", "headers": {"Authorization": "Bearer <token>"}}
    """
    try:
        p = _parse_args(args)
        url = p.get("url", "")
        if not url:
            return {"success": False, "error": "'url' é obrigatório."}

        method = p.get("method", "GET").upper()
        headers = p.get("headers", {})
        body = p.get("body")
        params = p.get("params")
        timeout = p.get("timeout", 15)

        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in valid_methods:
            return {"success": False, "error": f"Método inválido: {method}. Use: {', '.join(valid_methods)}"}

        logger.info(f"web_api: {method} {url}")

        sess = http_requests.Session()
        resp = sess.request(
            method=method,
            url=url,
            headers=headers,
            json=body if body else None,
            params=params,
            timeout=timeout
        )

        result = {
            "status": resp.status_code,
            "headers": dict(resp.headers),
        }

        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                result["data"] = resp.json()
            except Exception:
                result["text"] = resp.text[:5000]
        elif "text/" in content_type:
            result["text"] = resp.text[:5000]
        else:
            result["text"] = resp.text[:5000]

        if len(resp.text) > 5000:
            result["_truncated"] = True

        return {"success": True, "result": result}

    except http_requests.exceptions.Timeout:
        return {"success": False, "error": f"Timeout após {timeout}s ao acessar {url}"}
    except http_requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"Erro de conexão: {e}"}
    except http_requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Erro na requisição: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
