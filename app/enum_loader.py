import json
from pathlib import Path
from app.enums import DEFAULT_MACHINE_STATUS

ENUM_DIR = Path("config/enums")

class EnumLoader:
    def __init__(self):
        self._cache = {}

    def load(self, name: str):
        # cache
        if name in self._cache:
            return self._cache[name]

        path = ENUM_DIR / f"{name}.json"

        try:
            if not path.exists():
                raise FileNotFoundError(path)

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 保證是 list
            if not isinstance(data, list):
                raise ValueError(f"{path} must be a list")

            self._cache[name] = data
            return data

        except Exception as e:
            print(f"[ENUM] load failed: {name} ({e})")

            # fallback（轉成 list）
            if name == "machine_status":
                fallback = list(DEFAULT_MACHINE_STATUS.values())
                self._cache[name] = fallback
                return fallback

            return []
            
enum_loader = EnumLoader()
