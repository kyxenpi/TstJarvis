from tools.base import registry
import tools.browser
import tools.filesystem
import tools.terminal
import tools.google
import tools.python_runner

# Atalhos alternativos para tolerância de digitação do LLM
registry.tools["googledocs"] = registry.tools["google_docs"]

TOOLS_MANIFEST = registry.tools