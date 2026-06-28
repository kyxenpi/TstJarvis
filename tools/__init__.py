# tools/__init__.py

# Importa o registry e o decorator para ficarem fáceis de acessar se precisar
from tools.base import registry, tool

# Força o Python a carregar e registrar as ferramentas de cada arquivo
import tools.browser
import tools.filesystem
import tools.google
import tools.python_runner
import tools.registry
import tools.terminal