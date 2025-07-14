import threading
from typing import Dict, Any

class MemoryStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._store.get(user_id, {}).copy()

    def set(self, user_id: str, data: Dict[str, Any]):
        with self._lock:
            self._store[user_id] = data.copy()

    def update(self, user_id: str, data: Dict[str, Any]):
        with self._lock:
            if user_id not in self._store:
                self._store[user_id] = {}
            self._store[user_id].update(data)

    def clear(self, user_id: str):
        with self._lock:
            if user_id in self._store:
                del self._store[user_id]

memory_store = MemoryStore() 