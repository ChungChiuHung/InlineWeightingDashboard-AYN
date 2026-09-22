import asyncio
import logging
import random
import sys
import struct
from datetime import datetime

# 設定 Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - [PLC-SIM] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("plc-sim")

# 抑制新版 pymodbus 吵雜的 v4 棄用警告
logging.getLogger("pymodbus").setLevel(logging.ERROR)

# --- Import 檢查 ---
try:
    import pymodbus
except ImportError:
    logger.error("❌ 找不到 pymodbus 套件，請執行: pip install pymodbus")
    sys.exit(1)

# 1. Server Import
try:
    from pymodbus.server import StartAsyncTcpServer
except ImportError:
    logger.error("❌ 無法匯入 StartAsyncTcpServer。請確認您安裝的是 pymodbus v3.x")
    sys.exit(1)

# 2. Datastore Import
try:
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
    try:
        from pymodbus.datastore import ModbusSlaveContext
    except ImportError:
        try:
            from pymodbus.datastore.context import ModbusSlaveContext
        except ImportError:
            from pymodbus.datastore import ModbusDeviceContext as ModbusSlaveContext

except ImportError as e:
    logger.error(f"❌ Datastore 匯入失敗: {e}")
    sys.exit(1)

# 3. Device Identity
try:
    from pymodbus.device import ModbusDeviceIdentification
except ImportError:
    ModbusDeviceIdentification = None

# --- 設定區 ---
BIND_IP = "0.0.0.0"
BIND_PORT = 5020 

# 暫存器定義 (範圍擴大)
START_ADDRESS = 40001
REGISTER_COUNT = 200 

# Address Map
REG_WEIGHT_NOW = 40001      # Dword
REG_TIME_START = 40003      # Word*6
REG_TIME_END   = 40009      # Word*6
REG_BUCKET_STATS_BASE = 40015 
REG_BUCKET_RO_MIN_BASE = 40043
REG_B1_SETTING_BASE = 40101
REG_FISH_CODE = 40131       # String
REG_STATUS = 40135          # Word (1: RUN, 2: IDLE...)
REG_FISH_COUNT = 40141      # Dword (累計產量)

class PLCSimulator:
    def __init__(self, store):
        # 直接接收 ModbusSlaveContext (store) 進行操作，避開 context[slave_id] 的舊語法
        self.store = store
        
        # 生產參數
        self.production_interval = 3.0
        self.weight_hold_time = 0.8
        
        # 狀態參數
        self.current_status = 1 # 1: RUN
        self.total_count = 0
        
        self._init_defaults()

    def _init_defaults(self):
        logger.info("Initializing PLC defaults...")
        self._write_string(REG_FISH_CODE, "F001")
        self._update_status_register(1)
        self._write_dword(REG_FISH_COUNT, 0)
        
        # 初始化分規設定 (單位: g)
        # Bucket 1: 400-600g
        self._write_dword(40101, 400) # Min
        self._write_dword(40103, 600) # Max
        self._write_dword(40105, 500) # Target
        
        # Bucket 2: 600-800g
        self._write_dword(40043, 600) # Min (RO)
        self._write_dword(40107, 800) # Max
        self._write_dword(40109, 700) # Target
        
        # Bucket 3: 800-1000g
        self._write_dword(40045, 800)
        self._write_dword(40111, 1000)
        self._write_dword(40113, 900)

    # --- Register Helper Methods ---
    def _get_values_array(self):
        return self.store.simdata[0].values
        
    def _write_string(self, address, text):
        b = text.encode('ascii')
        while len(b) < 4: b += b'\x00'
        val1 = (b[0] << 8) | b[1]
        val2 = (b[2] << 8) | b[3]
        offset = address - START_ADDRESS
        arr = self._get_values_array()
        arr[offset] = val1
        arr[offset + 1] = val2

    def _write_dword(self, address, value):
        """寫入 32-bit (Big Endian)"""
        high = (value >> 16) & 0xFFFF
        low = value & 0xFFFF
        offset = address - START_ADDRESS
        arr = self._get_values_array()
        arr[offset] = high
        arr[offset + 1] = low

    def _read_dword(self, address):
        offset = address - START_ADDRESS
        arr = self._get_values_array()
        val1 = arr[offset]
        val2 = arr[offset + 1]
        return (val1 << 16) | val2

    def _read_fish_code(self):
        offset = REG_FISH_CODE - START_ADDRESS
        arr = self._get_values_array()
        val1 = arr[offset]
        val2 = arr[offset + 1]
        try:
            b = struct.pack('>HH', val1, val2)
            return b.decode('ascii').strip('\x00')
        except:
            return "UNKNOWN"
            
    def _update_status_register(self, status_code):
        self.current_status = status_code
        arr = self._get_values_array()
        arr[REG_STATUS - START_ADDRESS] = status_code

    # --- Main Loops ---
    async def run(self):
        logger.info("Starting simulation loops...")
        await asyncio.gather(
            self._loop_clock(),
            self._loop_status_simulation(),
            self._loop_production()
        )

    async def _loop_clock(self):
        while True:
            try:
                now = datetime.now()
                vals = [now.year, now.month, now.day, now.hour, now.minute, now.second]

                arr = self._get_values_array()

                offset_start = REG_TIME_START - START_ADDRESS
                arr[offset_start: offset_start+6] = vals

                offset_end = REG_TIME_END - START_ADDRESS
                arr[offset_end: offset_end+6] = vals

                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Clock error: {e}")
                await asyncio.sleep(1)

    async def _loop_status_simulation(self):
        """確保狀態維持在 RUN，偶爾切換 IDLE/ALARM"""
        logger.info("Status simulation loop started")
        while True:
            try:
                # 確保預設為 RUN
                if self.current_status != 1 and self.current_status != 2 and self.current_status != 3:
                     self._update_status_register(1)

                # 正常運轉 30~60 秒
                await asyncio.sleep(random.randint(30, 60))

                # 隨機事件
                if random.random() > 0.8:
                    if random.random() > 0.5:
                        logger.info("⏸️ Status: IDLE")
                        self._update_status_register(2)
                        await asyncio.sleep(5)
                    else:
                        logger.warning("⚠️ Status: ALARM")
                        self._update_status_register(3)
                        await asyncio.sleep(3)
                    
                    # 恢復 RUN
                    logger.info("✅ Status: RUN")
                    self._update_status_register(1)

            except Exception as e:
                logger.error(f"Status loop error: {e}")
                await asyncio.sleep(5)

    async def _loop_production(self):
        """生產秤重邏輯"""
        logger.info(f"Production loop started (Interval: {self.production_interval}s)")
        while True:
            try:
                if self.current_status == 1:
                    current_fish = self._read_fish_code()
                    
                    # 決定目標重 (400-1800g)
                    if current_fish == "F001": target, sigma = 600.0, 100.0
                    elif current_fish == "F002": target, sigma = 1000.0, 150.0
                    elif current_fish == "F003": target, sigma = 1500.0, 150.0
                    else: target, sigma = random.uniform(400, 1800), 200.0
                    
                    weight = random.gauss(target, sigma)
                    if weight < 400: weight = 400 + random.random() * 50
                    if weight > 1800: weight = 1800 - random.random() * 50
                    
                    weight_int = int(weight)
                    
                    # 更新計數與重量
                    self.total_count += 1
                    logger.info(f"🐟 #{self.total_count} {current_fish} | {weight_int}g")
                    
                    self._write_dword(REG_WEIGHT_NOW, weight_int)
                    self._write_dword(REG_FISH_COUNT, self.total_count)
                    
                    # 分規統計
                    self._update_bucket_stats(weight_int)
                    
                    # 歸零
                    asyncio.create_task(self._reset_weight_later(self.weight_hold_time))
                
                await asyncio.sleep(self.production_interval)

            except Exception as e:
                logger.error(f"Production loop error: {e}")
                await asyncio.sleep(1)

    def _update_bucket_stats(self, weight):
        # 簡化版分規邏輯
        target_bucket = -1
        b1_min = self._read_dword(40101)
        b1_max = self._read_dword(40103)
        if b1_min <= weight < b1_max: target_bucket = 1
        else:
            for i in range(2, 8):
                min_addr = 40043 + (i-2)*2
                max_addr = 40107 + (i-2)*4
                if self._read_dword(min_addr) <= weight < self._read_dword(max_addr):
                    target_bucket = i
                    break
        
        if target_bucket > 0:
            addr_total = 40015 + (target_bucket - 1) * 4
            addr_count = addr_total + 2
            self._write_dword(addr_total, self._read_dword(addr_total) + weight)
            self._write_dword(addr_count, self._read_dword(addr_count) + 1)

    async def _reset_weight_later(self, delay):
        await asyncio.sleep(delay)
        self._write_dword(REG_WEIGHT_NOW, 0)

async def main():
    # 將 Holding Register 區塊獨立出來
    hr_block = ModbusSequentialDataBlock(START_ADDRESS, [0] * REGISTER_COUNT)

    store = ModbusSlaveContext(
        hr=hr_block,
        ir=ModbusSequentialDataBlock(START_ADDRESS, [0] * REGISTER_COUNT),
        co=ModbusSequentialDataBlock(START_ADDRESS, [0] * REGISTER_COUNT),
        di=ModbusSequentialDataBlock(START_ADDRESS, [0] * REGISTER_COUNT)
    )
    slaves = {1: store}
    context = ModbusServerContext(slaves, single=False)
    
    # 直接將 store 傳入 Simulator，取代原本的 context
    sim = PLCSimulator(hr_block)
    
    identity = None
    if ModbusDeviceIdentification:
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'Simulated PLC'
        identity.ProductName = 'Fish Scale Sim (Fixed Status)'
        
    logger.info(f"🚀 Starting Modbus TCP Server on {BIND_IP}:{BIND_PORT}")
    
    sim_task = asyncio.create_task(sim.run())
    
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=(BIND_IP, BIND_PORT)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass