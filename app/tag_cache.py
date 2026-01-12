import time

class TagCache:
    def __init__(self, hub=None, historian=None):
        self.data = {}
        self.hub = hub
        self.historian = historian
        print("[TAGCACHE INIT] historian =", historian)

    async def update(self, name, value):
        ts = time.time()
        self.data[name] = {"value": value, "ts": ts}

        if self.hub:
            await self.hub.broadcast({
                "tag": name,
                "value": value,
                "ts": ts
            })

        if self.historian:
            self.historian.push(name, value, ts)
