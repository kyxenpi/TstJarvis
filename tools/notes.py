import json
from pathlib import Path
from datetime import datetime
from typing import Any
from tools.base import tool
from core.security import SecurityLevel

NOTES_FILE = Path.home() / ".koda_notes.json"


def _load_notes() -> list:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except Exception:
            return []
    return []


def _save_notes(notes: list) -> None:
    NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2))


@tool("note_save", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def note_save(args: Any) -> str:
    """Salva uma nota de texto rápidas notas locais."""
    text = args if isinstance(args, str) else args.get("text", "")
    if not text:
        return "Nada a salvar."

    notes = _load_notes()
    note = {
        "id": len(notes) + 1,
        "text": text,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    notes.append(note)
    _save_notes(notes)
    return f"Nota #{note['id']} salva."


@tool("note_list", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def note_list(args: Any = None) -> str:
    """Lista as últimas 10 notas salvas."""
    notes = _load_notes()
    if not notes:
        return "Nenhuma nota salva."
    lines = []
    for n in notes[-10:]:
        lines.append(f"#{n['id']} [{n['created']}] {n['text'][:80]}")
    return "\n".join(lines)


@tool("note_read", security_level=SecurityLevel.SAFE, cloud_compatible=False)
def note_read(args: Any) -> str:
    """Lê o conteúdo completo de uma nota pelo ID."""
    if isinstance(args, dict):
        note_id = int(args.get("id", 0))
    else:
        note_id = int(args) if str(args).isdigit() else 0
    notes = _load_notes()
    for n in notes:
        if n["id"] == note_id:
            return f"#{n['id']} [{n['created']}]\n{n['text']}"
    return f"Nota #{note_id} não encontrada."


@tool("note_delete", security_level=SecurityLevel.MEDIUM, cloud_compatible=False)
def note_delete(args: Any) -> str:
    """Remove uma nota pelo ID."""
    if isinstance(args, dict):
        note_id = int(args.get("id", 0))
    else:
        note_id = int(args) if str(args).isdigit() else 0
    notes = _load_notes()
    filtered = [n for n in notes if n["id"] != note_id]
    if len(filtered) == len(notes):
        return f"Nota #{note_id} não encontrada."
    _save_notes(filtered)
    return f"Nota #{note_id} removida."
