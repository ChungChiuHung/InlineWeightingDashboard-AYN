import asyncio
import logging
import random
import time
from typing import Any, Dict
from .gateway import BaseGateway
from .historian import Historian
from .ws_hub import WsHub

logger = logging.getLogger("sim_gateway")

class SimGateway(BaseGateway):
    def __init__(self, config: dict, historian: Historian, ws_hub: WsHub):
        super().__init__(config, historian, ws_hub)
        self.history_interval = config['system'].get('history_interval', 5.0)
        
        # 模擬狀態初始化
        self.fish_options = ["F001", "F002", "F003", "F004"]
        self.current_fish_code = self.fish_options[0] # 預設第一種
        self.batch_start_time = time.time()
        
        # 預設魚種變換時間 (10分鐘)
        self.batch_duration = 600.0
        
        # 重量模擬相關
        self.last_weight_change_time = 0
        self.weight_change_interval = 3.0  # 預設每 3 秒變換一次重量
        
        self.fixed_weight = None
        self.current_weight = 0.0

        # 從設定檔讀取模擬參數
        if 'simulation' in config['system']:
            sim_config = config['system']['simulation']
            
            # 設定固定重量
            if 'fixed_weight' in sim_config:
                self.fixed_weight = float(sim_config['fixed_weight'])
                logger.info(f"Simulation fixed weight set to: {self.fixed_weight}")
            
            # 設定重量更新頻率
            if 'weight_update_interval' in sim_config:
                self.weight_change_interval = float(sim_config['weight_update_interval'])
                logger.info(f"Simulation weight update interval set to: {self.weight_change_interval}s")

            # 設定魚種更新頻率
            if 'fish_update_interval' in sim_config:
                self.batch_duration = float(sim_config['fish_update_interval'])
                logger.info(f"Simulation fish update interval set to: {self.batch_duration}s")

        # 初始標籤
        self.update_tag("status", "IDLE")
        self.update_tag("fish_code", self.current_fish_code)
        self.update_tag("weight", 0.0)
        
        logger.info(f"SimGateway initialized. Fish batch duration: {self.batch_duration}s")

    async def tick(self):
        now = time.time()

        # --- 1. 模擬批次切換邏輯 (魚種變更) ---
        # 只有當經過了 batch_duration，才執行切換
        if now - self.batch_start_time > self.batch_duration:
            # 切換到下一個魚種
            current_idx = self.fish_options.index(self.current_fish_code)
            next_idx = (current_idx + 1) % len(self.fish_options)
            self.current_fish_code = self.fish_options[next_idx]
            
            # 重置批次時間
            self.batch_start_time = now
            
            # 更新 Tag
            self.update_tag("fish_code", self.current_fish_code)
            logger.info(f"[Sim] Batch changed. New Fish: {self.current_fish_code} (Next change in {self.batch_duration}s)")
        
        # 強制確保 tag 與內部狀態一致 (防呆，避免其他邏輯意外覆蓋)
        # 但只在不一致時才更新，避免觸發無謂的廣播
        if self.tags.get("fish_code") != self.current_fish_code:
             self.update_tag("fish_code", self.current_fish_code)

        # --- 2. 模擬機台狀態與重量 ---
        # 90% 機率是 RUN, 5% IDLE, 5% ALARM
        rand_val = random.random()
        
        current_status = "RUN" # 預設 RUN 以便觀察重量變化
        
        # 決定狀態
        if rand_val > 0.98:
             current_status = "ALARM"
        elif rand_val > 0.95:
             current_status = "IDLE"

        # 重量變換邏輯
        if current_status == "RUN":
            # 如果設定了固定重量，則直接使用
            if self.fixed_weight is not None:
                self.current_weight = self.fixed_weight
            # 否則，依照設定的時間間隔變換一次隨機重量
            elif now - self.last_weight_change_time > self.weight_change_interval:
                # 模擬重量波動: 500g (0.5kg) 為中心，隨機波動
                # 使用 uniform 讓數據在 0.1 ~ 3.0 之間跳動，方便觀察
                self.current_weight = round(random.uniform(0.1, 3.0), 2)
                self.last_weight_change_time = now
        else:
            self.current_weight = 0.0

        self.update_tag("status", current_status)
        self.update_tag("weight", self.current_weight)

        # --- 3. 模擬歷史數據記錄 ---
        # 依據 config 設定的間隔寫入 DB
        if now - self.last_update > self.history_interval:
            # 只有在 RUN 狀態且有重量時才記錄，模擬實際生產記錄
            if current_status == "RUN" and self.current_weight > 0:
                self.historian.log_data(self.tags)
            self.last_update = now