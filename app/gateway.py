import random
import time
import asyncio
from pymodbus.client import AsyncModbusTcpClient

class RealGateway:
    def __init__(self, plc_cfg):
        self.client = AsyncModbusTcpClient(
            host=plc_cfg["host"],
            port=plc_cfg["port"],
            timeout=plc_cfg["timeout"]
        )
        self.unit_id = plc_cfg["unit_id"]

    async def connect(self):
        await self.client.connect()

    async def read_block(self, start, count):
        rr = await self.client.read_holding_registers(
            address=start,
            count=count,
            slave=self.unit_id
        )
        if rr.isError():
            raise RuntimeError(rr)
        return rr.registers


FX5U_BASE = 40001

class SimGateway:
    def __init__(self):
        self.hr = [0] * 200

        self._write_word(40059, 1)  # RUN
        self._write_word(40060, 0)
        self._write_word(40061, 0)

        self.last_feed_time = time.time()
        self.last_fish = time.time()
        self.next_interval = random.uniform(0.5, 1.5)

        self.bucket_ranges = {
            i: (i*200, i*200 + 199)
            for i in range(1, 8)
        }

    async def connect(self):
        pass

    async def read_block(self, start, count):
        self._simulate_fish()
        offset = start - FX5U_BASE
        return self.hr[offset: offset + count]

    async def write_holding(self, addr, value):
        offset = addr - FX5U_BASE
        if isinstance(value, str):
            bs = value.encode("ascii")[:4]
            bs = bs.ljust(4, b"\x00")
            self.hr[offset] = bs[1] << 8 | bs[0]
            self.hr[offset + 1] = bs[3] << 8 | bs[2]

    def _write_word(self, addr, value):
        self.hr[addr - FX5U_BASE] = value & 0xFFFF

    def _write_dword(self, addr, value):
        o = addr - FX5U_BASE
        self.hr[o] = value & 0xFFFF
        self.hr[o+1] = (value >> 16) & 0xFFFF

    def _read_dword(self, addr):
        o = addr - FX5U_BASE
        return self.hr[o] | (self.hr[o+1] << 16)
