import time
import math
import random

class SimulatedGateway:
    def __init__(self, tags):
        self.tags = tags
        self.state = {}
        self.start_time = time.time()

        for tag in tags:
            self.state[tag["name"]] = tag.get("sim", {}).get("min", 0)

    async def connect(self):
        return True  # 永遠成功

    async def read_holding(self, tag):
        cfg = tag.get("sim", {})
        pattern = cfg.get("pattern", "constant")

        v = self.state[tag["name"]]

        if pattern == "ramp":
            v += cfg.get("step", 1)
            if v > cfg.get("max", 100):
                v = cfg.get("min", 0)

        elif pattern == "sine":
            t = time.time() - self.start_time
            min_v = cfg.get("min", 0)
            max_v = cfg.get("max", 100)
            v = int(
                min_v + (max_v - min_v) *
                (0.5 + 0.5 * math.sin(t))
            )

        elif pattern == "random":
            v = random.randint(
                cfg.get("min", 0),
                cfg.get("max", 100)
            )

        self.state[tag["name"]] = v
        return [v]
