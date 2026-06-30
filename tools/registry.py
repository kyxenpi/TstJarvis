from tools.base import registry
import tools.browser
import tools.filesystem
import tools.terminal
import tools.google
import tools.python_runner
import tools.web_search
import tools.calculator
import tools.system_info
import tools.notes
import tools.web_api

# Google Docs
registry.tools["googledocs"] = registry.tools["google_docs"]

# Notes
registry.tools["nota"] = registry.tools["note_save"]
registry.tools["note"] = registry.tools["note_save"]

# Calculator
registry.tools["calcular"] = registry.tools["calculate"]

# Web search
registry.tools["buscar"] = registry.tools["web_search"]
registry.tools["pesquisar"] = registry.tools["web_search"]
registry.tools["fetch"] = registry.tools["web_fetch"]
registry.tools["ler_url"] = registry.tools["web_fetch"]

# System
registry.tools["processos"] = registry.tools["active_processes"]
registry.tools["info"] = registry.tools["system_info"]

# Calendar
registry.tools["agenda_adicionar"] = registry.tools["google_calendar_add"]
registry.tools["agenda_listar"] = registry.tools["google_calendar_list"]
registry.tools["agenda_remover"] = registry.tools["google_calendar_remove"]

# Gmail
registry.tools["email_buscar"] = registry.tools["gmail_search"]
registry.tools["email_enviar"] = registry.tools["gmail_send"]

# YouTube
registry.tools["youtube"] = registry.tools["youtube_search"]

# Contacts
registry.tools["contatos"] = registry.tools["google_contacts"]

# Sheets
registry.tools["planilhas"] = registry.tools["google_sheets"]

# Web API custom
registry.tools["api"] = registry.tools["web_api"]

TOOLS_MANIFEST = registry.tools
