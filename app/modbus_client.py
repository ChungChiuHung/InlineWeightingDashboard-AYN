import logging
import asyncio
from pymodbus.client import AsyncModbusTcpClient

logger = logging.getLogger("modbus")

class ModbusClient:
    def __init__(self, host: str, port: int, max_retries: int = 3, retry_delay: float = 2.0):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = AsyncModbusTcpClient(host, port=port)
        self.connected = False
        self.connection_attempts = 0

    async def connect(self) -> bool:
        """建立連線 with retry logic"""
        for attempt in range(1, self.max_retries + 1):
            try:
                self.connected = await self.client.connect()
                if self.connected:
                    logger.info(f"Connected to PLC at {self.host}:{self.port}")
                    self.connection_attempts = 0
                    return True
                else:
                    logger.warning(f"Failed to connect to PLC at {self.host}:{self.port} (attempt {attempt}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Connection exception on attempt {attempt}/{self.max_retries}: {e}")
            
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)
        
        self.connection_attempts += 1
        return False

    def close(self):
        """關閉連線"""
        try:
            self.client.close()
            self.connected = False
            logger.info("Connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    async def read_holding_registers(self, address: int, count: int):
        """讀取保持暫存器 (Holding Registers) with error handling"""
        if not self.connected:
            logger.warning("Cannot read: not connected to PLC")
            return None
        try:
            # slave=1 是 Modbus TCP 的預設 Unit ID
            rr = await self.client.read_holding_registers(address, count, slave=1)
            if rr.isError():
                logger.error(f"Modbus Read Error at {address}: {rr}")
                return None
            return rr.registers
        except Exception as e:
            logger.error(f"Read Exception at address {address}: {e}")
            self.connected = False
            return None

    async def write_register(self, address: int, value: int):
        """寫入單個暫存器 (用於控制) with error handling"""
        if not self.connected:
            logger.warning("Cannot write: not connected to PLC")
            return False
        try:
            rr = await self.client.write_register(address, value, slave=1)
            if rr.isError():
                logger.error(f"Modbus Write Error at {address}: {rr}")
                return False
            logger.info(f"Successfully wrote {value} to register {address}")
            return True
        except Exception as e:
            logger.error(f"Write Exception at address {address}: {e}")
            self.connected = False
            return False