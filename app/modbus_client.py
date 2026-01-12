import asyncio
from pymodbus.client import AsyncModbusTcpClient

class RealModbusGateway:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = AsyncModbusTcpClient(
            host=cfg["host"],
            port=cfg["port"],
            timeout=cfg["timeout"]
        )

    async def connect(self):
        await self.client.connect()

    async def read_holding(self, address, count, unit):
        rr = await self.client.read_holding_registers(
            address=address,
            count=count,
            slave=unit
        )
        if rr.isError():
            raise RuntimeError(rr)
        return rr.registers
