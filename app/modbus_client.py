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

    async def _execute_command(self, func, *args, **kwargs):
        """
        通用執行 Modbus 指令的 helper。
        自動處理 'slave', 'unit' 的相容性問題。
        """
        slave_id = 1
        
        # Strategy 1: 嘗試使用標準 'slave' 關鍵字 (v3.x)
        try:
            kwargs['slave'] = slave_id
            return await func(*args, **kwargs)
        except TypeError as e_slave:
            if "unexpected keyword argument 'slave'" not in str(e_slave):
                # 如果錯誤不是關於 slave 參數，則直接拋出
                raise e_slave
            
            # Strategy 2: 嘗試使用舊版 'unit' 關鍵字 (v2.x)
            kwargs.pop('slave', None)
            try:
                kwargs['unit'] = slave_id
                return await func(*args, **kwargs)
            except TypeError as e_unit:
                if "unexpected keyword argument 'unit'" not in str(e_unit):
                    raise e_unit

                # Strategy 3: 放棄指定 slave ID，使用預設值
                # 既然連線成功且能呼叫，這表示不需要顯式傳遞 slave ID
                # 將警告降級為 debug 以保持日誌乾淨
                logger.debug(f"Modbus call fallback: ignoring slave ID (using default). Error was: {e_unit}")
                kwargs.pop('unit', None)
                return await func(*args, **kwargs)

    async def read_holding_registers(self, address: int, count: int):
        """
        讀取保持暫存器 (Holding Registers) with error handling & chunking.
        如果 count > 125，自動拆分為多個請求。
        """
        if not self.connected:
            logger.warning("Cannot read: not connected to PLC")
            return None

        # Modbus TCP limit per request is usually 125 registers
        MAX_READ_SIZE = 125
        
        # 如果請求數量在限制內，直接執行
        if count <= MAX_READ_SIZE:
            return await self._read_chunk(address, count)
        
        # 如果超過限制，進行拆分讀取 (Chunking)
        full_data = []
        for i in range(0, count, MAX_READ_SIZE):
            chunk_addr = address + i
            chunk_count = min(MAX_READ_SIZE, count - i)
            
            chunk_data = await self._read_chunk(chunk_addr, chunk_count)
            if chunk_data is None:
                # 任何一個區塊失敗，視為整體失敗
                return None
            
            full_data.extend(chunk_data)
            
        return full_data

    async def _read_chunk(self, address: int, count: int):
        """實際執行單次讀取請求 (內部使用)"""
        try:
            # 使用 kwargs 傳遞 count，避免位置參數錯誤
            rr = await self._execute_command(self.client.read_holding_registers, address, count=count)
            
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
            # 使用 kwargs 傳遞 value，避免位置參數錯誤
            rr = await self._execute_command(self.client.write_register, address, value=value)
            
            if rr.isError():
                logger.error(f"Modbus Write Error at {address}: {rr}")
                return False
            logger.info(f"Successfully wrote {value} to register {address}")
            return True
        except Exception as e:
            logger.error(f"Write Exception at address {address}: {e}")
            self.connected = False
            return False