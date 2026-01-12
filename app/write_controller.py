import time

class WriteController:
    def __init__(self, wo_cfg):
        self.tags = {t["name"]: t for t in wo_cfg["tags"]}
        self.rate_limit = wo_cfg.get("rate_limit_ms", 500) / 1000
        self.last_write = {}

    def validate(self, name, value):
        if name not in self.tags:
            raise PermissionError("Tag not writable")

        t = self.tags[name]

        if t["type"] in ("word", "dword"):
            if "min" in t and value < t["min"]:
                raise ValueError("Value below min")
            if "max" in t and value > t["max"]:
                raise ValueError("Value above max")

        now = time.time()
        last = self.last_write.get(name, 0)
        if now - last < self.rate_limit:
            raise RuntimeError("Write rate limited")

        self.last_write[name] = now
        return t
