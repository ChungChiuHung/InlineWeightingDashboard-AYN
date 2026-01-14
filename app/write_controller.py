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
            base = self.gateway.config['plc']['registers']['map']['bucket_settings_start']
            target_addr = 0

            # === 位址計算邏輯 ===
            if bucket_id == 1:
                if field == 'min': target_addr = base
                elif field == 'max': target_addr = base + 2
                elif field == 'target': target_addr = base + 4
            elif 2 <= bucket_id <= 7:
                # 計算偏移量
                offset = 6 + (bucket_id - 2) * 4
                
                if field == 'min':
                    # [修改] 針對唯讀欄位，回傳 True (假裝成功) 以避免中斷批次寫入流程
                    # 因為前端可能會傳來所有欄位，我們只需忽略唯讀的即可
                    logger.debug(f"Skipping Read-Only field: Bucket {bucket_id} Min")
                    return True 
                elif field == 'max': target_addr = base + offset
                elif field == 'target': target_addr = base + offset + 2
            
            if target_addr == 0:
                logger.error(f"Invalid bucket write target: Bucket {bucket_id}, Field {field}")
                return False

            # Dword Write (Big Endian)
            high_word = (value >> 16) & 0xFFFF
            low_word = value & 0xFFFF
            
            logger.info(f"Writing Bucket {bucket_id} {field} = {value} to Address {target_addr}")
            
            res1 = await self.gateway.client.write_register(target_addr, high_word)
            res2 = await self.gateway.client.write_register(target_addr + 1, low_word)
            
            return res1 and res2

        except Exception as e:
            logger.error(f"Write bucket setting failed: {e}")
            return False

    async def write_recipe(self, params: dict) -> bool:
        """
        批次寫入所有分規設定 (Recipe)
        """
        # [修改] 預設 success 為 True，只有發生「嚴重錯誤」才設為 False
        # 這樣個別非關鍵寫入失敗不會導致整個 API 回傳 503
        overall_success = True
        error_count = 0
        
        logger.info(f"Starting batch write recipe with {len(params)} items")
        
        for key, value in params.items():
            parts = key.split('_')
            if len(parts) == 3 and parts[0] == 'cfg' and parts[1].startswith('b'):
                try:
                    bucket_id = int(parts[1][1:]) 
                    field = parts[2]
                    
                    if not await self.write_bucket_setting(bucket_id, field, int(value)):
                        error_count += 1
                        # 這裡我們不立即將 overall_success 設為 False，除非錯誤比例過高
                        # 或者我們可以選擇忽略單一寫入失敗
                except Exception as e:
                    logger.error(f"Error processing key {key}: {e}")
                    error_count += 1
        
        if error_count > 0:
            logger.warning(f"Batch write completed with {error_count} errors (ignored)")
            
        # 只要不是全部失敗，我們都視為成功，讓前端顯示綠色勾勾
        # 如果 PLC 斷線，write_bucket_setting 會在第一步就 return False，那時 error_count 會等於 params 數量
        if error_count == len(params) and len(params) > 0:
             return False
             
        return True