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
        old_value = self.tags.get(name)
        if value != old_value:
            self.tags[name] = value
            asyncio.create_task(self.ws_hub.broadcast({name: value}))
            
            # 簡單的歷史記錄觸發邏輯：當重量大於 0 且穩定時 (這裡簡化為每次變化都記)
            # 實際專案通常會加上 "重量穩定訊號" 判斷
            if name == 'weight' and isinstance(value, (int, float)) and value > 0:
                 pass # 可在此呼叫 historian.log_data

    def get_snapshot(self) -> dict:
        return self.tags

class RealGateway(BaseGateway):
    def __init__(self, config: dict, historian: Historian, ws_hub: WsHub):
        super().__init__(config, historian, ws_hub)
        self.client = ModbusClient(config['plc']['host'], config['plc']['port'])
        
        # [修改] 將設定檔中的地址對應表傳給 Parser
        self.parser = TagParser(config['plc']['registers']['map'])
        
        # [修改] 從設定檔讀取讀取範圍
        self.start_addr = config['plc']['registers']['read_start']
        self.read_count = config['plc']['registers']['read_count']

    async def start(self):
        if not await self.client.connect():
            logger.error("Failed to connect to PLC.")
            return
        await super().start()

    async def stop(self):
        await super().stop()
        self.client.close()

    async def tick(self):
        # [修改] 使用設定檔中的地址與長度
        regs = await self.client.read_holding_registers(self.start_addr, self.read_count)
        
        if regs:
            # 解析數據
            parsed_data = self.parser.parse_block(regs, self.start_addr)
            
            for key, val in parsed_data.items():
                self.update_tag(key, val)
                
            # 定期寫入歷史 (每 5 秒)
            if time.time() - self.last_update > 5.0:
                # 這裡需要組合完整的 data 字典才能寫入 DB
                # 簡單起見，我們將目前所有 tags 傳入
                # 注意：這可能會因為某些 tag 尚未有值而缺欄位，Historian 需處理
                if 'fish_code' in self.tags:
                     self.historian.log_data(self.tags)
                self.last_update = time.time()

class SimGateway(BaseGateway):
    async def tick(self):
        import random
        statuses = ["RUN", "IDLE", "ALARM"]
        current_status = statuses[0] if random.random() > 0.1 else statuses[1]
        
        self.update_tag("status", current_status)
        self.update_tag("weight", round(random.uniform(0, 3.0), 2))
        
        fish_codes = ["F001", "F002", "F003"]
        self.update_tag("fish_code", random.choice(fish_codes))