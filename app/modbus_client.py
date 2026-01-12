import logging
from pymodbus.client import AsyncModbusTcpClient

logger = logging.getLogger("modbus")

class ModbusClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(host, port=port)
        self.connected = False

    async def connect(self) -> bool:
        """建立連線"""
        try:
            self.connected = await self.client.connect()
            if self.connected:
                logger.info(f"Connected to PLC at {self.host}:{self.port}")
            else:
                logger.warning(f"Failed to connect to PLC at {self.host}:{self.port}")
            return self.connected
        except Exception as e:
            logger.error(f"Connection exception: {e}")
            return False

    def close(self):
        """關閉連線"""
        self.client.close()
        self.connected = False
        logger.info("Connection closed")

    async def read_holding_registers(self, address: int, count: int):
        """讀取保持暫存器 (Holding Registers)"""
        if not self.connected:
            return None
        try:
            # slave=1 是 Modbus TCP 的預設 Unit ID
            rr = await self.client.read_holding_registers(address, count, slave=1)
            if rr.isError():
                logger.error(f"Modbus Read Error at {address}: {rr}")
                return None
            return rr.registers
        except Exception as e:
            logger.error(f"Read Exception: {e}")
            return None

    async def write_register(self, address: int, value: int):
        """寫入單個暫存器 (用於控制)"""
        if not self.connected:
            return False
        try:
            rr = await self.client.write_register(address, value, slave=1)
            if rr.isError():
                logger.error(f"Modbus Write Error at {address}: {rr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Write Exception: {e}")
            return False