import time
from typing import Any, Dict, Optional

class CacheManager:
    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        item = self._cache[key]
        if time.time() > item["expires_at"]:
            del self._cache[key]
            return None
        return item["value"]

    def invalidate(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

agent_cache = CacheManager()