import time

class RegisterCache:
    def __init__(self):
        self.blocks = {}

    def update_block(self, group, registers):
        self.blocks[group] = {
            "registers": registers,
            "ts": time.time()
        }

    def get_block(self, group):
        return self.blocks.get(group)
