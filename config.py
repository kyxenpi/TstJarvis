import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "database" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)

@dataclass(frozen=True)
class Config:
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("API_KEY", os.getenv("GROQ_API_KEY", "")))
    TELEGRAM_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_TOKEN", ""))
    
    MODEL_PRIMARY: str = "llama-3.3-70b-versatile"
    MODEL_SECONDARY: str = "llama-3.1-8b-instant"
    MAX_AGENT_STEPS: int = 8
    DEFAULT_TIMEOUT: float = 45.0
    
    GOOGLE_CREDENTIALS_JSON: str = field(default_factory=lambda: os.getenv("GOOGLE_CREDENTIALS_JSON", ""))
    GOOGLE_TOKEN_JSON: str = field(default_factory=lambda: os.getenv("GOOGLE_TOKEN_JSON", ""))
    
    SCOPES: List[str] = field(default_factory=lambda: [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/cloud_search',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/youtube'
    ])

settings = Config()