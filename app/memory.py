import chromadb
from typing import Dict, Any
import json

class MemoryStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("user_data")

    def get(self, user_id: str) -> Dict[str, Any]:
        try:
            results = self.collection.get(ids=[user_id])
            if results['documents'] and results['documents'][0]:
                return json.loads(results['documents'][0])
            return {}
        except:
            return {}

    def set(self, user_id: str, data: Dict[str, Any]):
        try:
            self.collection.upsert(
                ids=[user_id],
                documents=[json.dumps(data)]
            )
        except:
            pass

    def update(self, user_id: str, data: Dict[str, Any]):
        existing = self.get(user_id)
        existing.update(data)
        self.set(user_id, existing)

    def clear(self, user_id: str):
        try:
            self.collection.delete(ids=[user_id])
        except:
            pass

memory_store = MemoryStore()