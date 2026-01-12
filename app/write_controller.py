import logging

logger = logging.getLogger("control")

class WriteController:
    def __init__(self, gateway):
        self.gateway = gateway

    async def set_fish_type(self, code: str) -> bool:
        """寫入魚種代碼 (String)"""
        if hasattr(self.gateway, 'client') and not self.gateway.client.connected:
             logger.warning("Write rejected: PLC disconnected")
             return False

        logger.info(f"Setting fish type: {code}")
        
        # Sim Mode
        if hasattr(self.gateway, 'update_tag') and not hasattr(self.gateway, 'client'):
            self.gateway.update_tag('fish_code', code)
            return True

        try:
            start_addr = self.gateway.config['plc']['registers']['map']['fish_code']
            b = code.encode('ascii')
            val1 = (b[0] << 8) | b[1]
            val2 = (b[2] << 8) | b[3]
            
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
        if hasattr(self.gateway, 'client') and not self.gateway.client.connected:
             logger.warning("Write rejected: PLC disconnected")
             return False
             
        # Sim Mode
        if hasattr(self.gateway, 'update_tag') and not hasattr(self.gateway, 'client'):
            tag_name = f"cfg_b{bucket_id}_{field}"
            self.gateway.update_tag(tag_name, value)
            return True

        try:
            base = self.gateway.config['plc']['registers']['map']['bucket_settings_start'] # 40101
            target_addr = 0

            # 計算位址邏輯
            if bucket_id == 1:
                if field == 'min': target_addr = base
                elif field == 'max': target_addr = base + 2
                elif field == 'target': target_addr = base + 4
            elif 2 <= bucket_id <= 7:
                # Bucket 2 starts at base + 6 (40107)
                # Each bucket takes 4 words (Max, Target)
                offset = 6 + (bucket_id - 2) * 4
                if field == 'min':
                    logger.warning(f"Bucket {bucket_id} Min is Read-Only")
                    return False
                elif field == 'max': target_addr = base + offset
                elif field == 'target': target_addr = base + offset + 2
            
            if target_addr == 0:
                logger.error("Invalid bucket write target")
                return False

            # Dword Write (Big Endian)
            # High Word at addr, Low Word at addr+1
            high_word = (value >> 16) & 0xFFFF
            low_word = value & 0xFFFF
            
            logger.info(f"Writing Bucket {bucket_id} {field} = {value} to {target_addr}")
            
            res1 = await self.gateway.client.write_register(target_addr, high_word)
            res2 = await self.gateway.client.write_register(target_addr + 1, low_word)
            
            return res1 and res2

        except Exception as e:
            logger.error(f"Write bucket setting failed: {e}")
            return False