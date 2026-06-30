from typing import List, Dict
from agent.prompts import get_system_prompt
from database.memory_db import db


class ContextManager:
    SYSTEM_TOKENS_ESTIMATE = 2000

    @staticmethod
    def build(session_id: str, max_history: int = 8) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": get_system_prompt()}]

        history_rows = db.get_history(session_id, limit=max_history)
        for msg in history_rows:
            role = msg["role"]
            content = msg["content"]
            if role == "assistant":
                messages.append({"role": "assistant", "content": content})
            elif role == "system":
                messages.append({"role": "system", "content": content})
            else:
                messages.append({"role": "user", "content": content})

        last_doc = db.get_metadata("last_google_doc_id")
        if last_doc:
            messages.append({
                "role": "system",
                "content": f"[Contexto: Último Google Doc: '{last_doc}']"
            })

        return messages
