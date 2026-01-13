import logging

logger = logging.getLogger("control")

class WriteController:
    def __init__(self, gateway):
        self.gateway = gateway

    async def set_fish_type(self, code: str) -> bool:
        """寫入魚種代碼 (String) 到 PLC"""
        if not self.gateway.client.connected:
             logger.warning("Write rejected: PLC disconnected")
             return False

        logger.info(f"Setting fish type: {code}")
        
        try:
            # 從 config 讀取起始位址 (預設 40131)
            start_addr = self.gateway.config['plc']['registers']['map']['fish_code']
            
            # String 轉 ASCII 並補滿 4 bytes
            b = code.encode('ascii')
            while len(b) < 4: b += b'\x00'
            
            val1 = (b[0] << 8) | b[1]
            val2 = (b[2] << 8) | b[3]
            
            # 連續寫入 2 個暫存器
            res1 = await self.gateway.client.write_register(start_addr, val1)
            res2 = await self.gateway.client.write_register(start_addr + 1, val2)
            
            return res1 and res2
        except Exception as e:
            logger.error(f"Write fish code failed: {e}")
            return False

    async def write_bucket_setting(self, bucket_id: int, field: str, value: int) -> bool:
        """
        寫入分規設定 (Dword)
        bucket_id: 1~7
        field: 'min', 'max', 'target'
        value: 32-bit integer
        """
        if not self.gateway.client.connected:
             logger.warning("Write rejected: PLC disconnected")
             return False

        try:
            # 從 config 讀取 bucket_settings_start (預設 40101)
            base = self.gateway.config['plc']['registers']['map']['bucket_settings_start']
            target_addr = 0

            # === 位址計算邏輯 ===
            # Bucket 1: Min(40101), Max(40103), Target(40105)
            # Bucket 2: Max(40107), Target(40109)
            # ...
            
            if bucket_id == 1:
                if field == 'min': target_addr = base
                elif field == 'max': target_addr = base + 2
                elif field == 'target': target_addr = base + 4
            elif 2 <= bucket_id <= 7:
                # 計算偏移量:
                # Bucket 2 從 base + 6 (40107) 開始
                # 每個分規間隔 4 Words (Max + Target)
                offset = 6 + (bucket_id - 2) * 4
                
                if field == 'min':
                    logger.warning(f"Bucket {bucket_id} Min is Read-Only (PLC Register R2042~)")
                    return False # 唯讀不可寫
                elif field == 'max': target_addr = base + offset
                elif field == 'target': target_addr = base + offset + 2
            
            if target_addr == 0:
                logger.error(f"Invalid bucket write target: Bucket {bucket_id}, Field {field}")
                return False

            # Dword Write (Big Endian 拆分為兩個 Word)
            high_word = (value >> 16) & 0xFFFF
            low_word = value & 0xFFFF
            
            logger.info(f"Writing Bucket {bucket_id} {field} = {value} to Address {target_addr}")
            
            # 連續寫入 High Word 和 Low Word
            res1 = await self.gateway.client.write_register(target_addr, high_word)
            res2 = await self.gateway.client.write_register(target_addr + 1, low_word)
            
            return res1 and res2

        except Exception as e:
            logger.error(f"Write bucket setting failed: {e}")
            return False

    async def write_recipe(self, params: dict) -> bool:
        """
        批次寫入所有分規設定 (Recipe)
        params 範例: {"cfg_b1_min": 400, "cfg_b1_max": 600, ...}
        """
        success = True
        logger.info(f"Starting batch write recipe with {len(params)} items")
        
        for key, value in params.items():
            # 解析 key 格式: "cfg_b{id}_{field}"
            parts = key.split('_')
            # 確保 key 格式正確且 bucket_id 有效
            if len(parts) == 3 and parts[0] == 'cfg' and parts[1].startswith('b'):
                try:
                    bucket_id = int(parts[1][1:]) # 取出 b1 -> 1
                    field = parts[2]
                    
                    # 嘗試寫入單個設定，如果失敗則標記 success 為 False 但繼續執行其他寫入
                    if not await self.write_bucket_setting(bucket_id, field, int(value)):
                        logger.warning(f"Failed to write item: {key}")
                        success = False
                except Exception as e:
                    logger.error(f"Error parsing/writing key {key}: {e}")
                    success = False
        
        if success:
            logger.info("Batch write completed successfully")
        else:
            logger.warning("Batch write completed with some errors")
            
        return success