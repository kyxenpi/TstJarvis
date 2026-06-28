from typing import List, Dict
from agent.prompts import get_system_prompt
from database.memory_db import db

class ContextManager:
    @staticmethod
    def build(session_id: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": get_system_prompt()}]
        
        history_rows = db.get_history(session_id, limit=10)
        for msg in history_rows:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        last_doc = db.get_metadata("last_google_doc_id")
        if last_doc:
            messages.append({
                "role": "system", 
                "content": f"[Contexto de Sistema: O ID do último Google Doc manipulado é '{last_doc}']"
            })
            
        return messages