import time
from typing import Dict, Any

class TagCache:
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def update(self, name: str, value: Any):
        self._data[name] = {
            "value": value,
            "ts": time.time()
        }

    def snapshot(self):
        return self._data.copy()
