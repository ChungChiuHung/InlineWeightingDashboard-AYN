import asyncio
import logging
import time
from typing import Dict, Any, Optional
from .modbus_client import ModbusClient
from .historian import Historian
from .ws_hub import WsHub
from .parser import TagParser

logger = logging.getLogger("gateway")

class BaseGateway:
    def __init__(self, config: dict, historian: Historian, ws_hub: WsHub):
        self.config = config
        self.historian = historian
        self.ws_hub = ws_hub
        self.running = False
        self.tags: Dict[str, Any] = {}
        self.last_update = 0.0
        
        # [修改] 用於追蹤重量變化，實現 Event-based Logging
        # 初始化為 -1 確保第一次讀取 0 也會被視為變化（如果需要）
        # 但這裡是為了偵測上升緣，所以初始 0 即可
        self._prev_weight = 0.0
        self._stable_weight_counter = 0

    async def start(self):
        self.running = True
        logger.info("Gateway started.")
        while self.running:
            start_time = time.time()
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.config['plc']['poll_interval'] - elapsed)
            await asyncio.sleep(sleep_time)

    async def stop(self):
        self.running = False
        logger.info("Gateway stopped.")

    async def tick(self):
        raise NotImplementedError

    def update_tag(self, name: str, value: Any):
        # 檢查數值是否真的改變
        old_value = self.tags.get(name)
        
        # 更新 Tags 字典
        self.tags[name] = value
        
        # 只要有任何 Tag 更新，就視為 Gateway 活著
        self.last_update = time.time()
        
        # 只有當數值改變時才廣播 (節省頻寬)
        if value != old_value:
            asyncio.create_task(self.ws_hub.broadcast({name: value}))
            
        # [關鍵] 觸發 Event-based Logging
        # 無論數值是否改變，只要是 'weight' 標籤被更新（代表一次 polling 完成），就檢查是否需要紀錄
        # 注意：我們需要在這裡傳入 current value，因為 self.tags['weight'] 已經是新的了
        if name == 'weight':
            self._check_and_log_production(value)

    def _check_and_log_production(self, current_weight):
        """
        核心紀錄邏輯：
        當重量從「無負載 (<= Threshold)」變為「有效負載 (> Threshold)」時，視為一隻新魚通過。
        """
        try:
            # 閾值：大於 10g 視為有魚
            THRESHOLD = 10.0 
            
            # 確保 current_weight 是數值
            if not isinstance(current_weight, (int, float)):
                return

            # 上升緣偵測 (Rising Edge): 
            # 上一次 (self._prev_weight) 是空的/零，這一次 (current_weight) 有重量
            if self._prev_weight <= THRESHOLD and current_weight > THRESHOLD:
                
                # 取得關聯資料
                fish_code = self.tags.get('fish_code', 'UNKNOWN')
                status = self.tags.get('status', 'RUN')
                
                # 只有在非 UNKNOWN 狀態下記錄 (可選)
                log_data = {
                    'fish_code': fish_code,
                    'weight': current_weight,
                    'status': status
                }
                
                logger.info(f"🐟 [Production Log] New Fish: {log_data}")
                
                # 寫入資料庫
                self.historian.log_data(log_data)
            
            # 更新上一次的重量，供下次比較
            self._prev_weight = current_weight
            
        except Exception as e:
            logger.error(f"Logging check failed: {e}")

    def get_snapshot(self) -> dict:
        return self.tags

class RealGateway(BaseGateway):
    def __init__(self, config: dict, historian: Historian, ws_hub: WsHub):
        super().__init__(config, historian, ws_hub)
        self.client = ModbusClient(
            config['plc']['host'], 
            config['plc']['port'],
            max_retries=3,
            retry_delay=2.0
        )
        
        self.parser = TagParser(config['plc']['registers']['map'])
        self.start_addr = config['plc']['registers']['read_start']
        self.read_count = config['plc']['registers']['read_count']
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

    async def start(self):
        if not await self.client.connect():
            logger.error("Failed to connect to PLC. Will retry in polling loop.")
        await super().start()

    async def stop(self):
        await super().stop()
        self.client.close()

    async def tick(self):
        if not self.client.connected and self.reconnect_attempts < self.max_reconnect_attempts:
            logger.info(f"Attempting to reconnect to PLC (attempt {self.reconnect_attempts + 1})")
            if await self.client.connect():
                logger.info("Successfully reconnected to PLC")
                self.reconnect_attempts = 0
            else:
                self.reconnect_attempts += 1
                return
        
        if not self.client.connected:
            return
            
        # 讀取暫存器
        regs = await self.client.read_holding_registers(self.start_addr, self.read_count)
        
        if regs:
            self.reconnect_attempts = 0
            # 解析數據
            parsed_data = self.parser.parse_block(regs, self.start_addr)
            
            # 更新每一個 Tag
            for key, val in parsed_data.items():
                self.update_tag(key, val)
        else:
            logger.warning("Failed to read from PLC, connection may be lost")