import re
import requests
from html.parser import HTMLParser
from typing import Any
from tools.base import tool
from core.security import SecurityLevel


@tool("web_search", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def web_search(args: Any) -> str:
    """Busca na web usando DuckDuckGo e retorna os primeiros resultados."""
    query = args if isinstance(args, str) else args.get("query", "")
    if not query:
        return "Nada a pesquisar."

    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15
        )
        if resp.status_code != 200:
            return f"Erro na busca: HTTP {resp.status_code}"

        class ResultParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._capture = False
                self._text = ""

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                    self._capture = True
                    self._text = ""

            def handle_data(self, data):
                if self._capture:
                    self._text += data

            def handle_endtag(self, tag):
                if self._capture and tag == "a":
                    self._capture = False
                    if self._text.strip():
                        self.results.append(self._text.strip())

        parser = ResultParser()
        parser.feed(resp.text)
        results = parser.results[:5]

        if not results:
            for line in resp.text.split("\n"):
                if "class=\"result__snippet\"" in line:
                    m = re.search(r'>([^<]+)<', line)
                    if m:
                        results.append(m.group(1))
            results = results[:5]

        if not results:
            return "Nenhum resultado encontrado."

        output = f"Resultados para '{query}':\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r}\n"
        return output.strip()

    except requests.Timeout:
        return "Busca excedeu o tempo limite."
    except Exception as e:
        return f"Erro na busca: {str(e)}"


@tool("web_fetch", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def web_fetch(args: Any) -> str:
    """Acessa uma URL e retorna o conteudo em texto puro (como o Claude le paginas)."""
    url = args if isinstance(args, str) else args.get("url", "")
    if not url:
        return "Nenhuma URL fornecida."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=20
        )
        if resp.status_code != 200:
            return f"Erro ao acessar {url}: HTTP {resp.status_code}"

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "noscript"):
                    self._skip = True
                if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
                    self.parts.append("\n")

            def handle_endtag(self, tag):
                if tag in ("script", "style", "noscript"):
                    self._skip = False

            def handle_data(self, data):
                if not self._skip and data.strip():
                    self.parts.append(data.strip())

        extractor = TextExtractor()
        extractor.feed(resp.text)
        text = " ".join(extractor.parts)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()

        if len(text) > 8000:
            text = text[:8000] + "\n\n... [truncado]"

        if not text:
            return f"URL acessada, mas nenhum texto extraivel: {url}"

        return f"Conteudo de {url}:\n\n{text}"

    except requests.Timeout:
        return f"Timeout ao acessar {url} (20s)."
    except Exception as e:
        return f"Erro ao acessar {url}: {str(e)}"
