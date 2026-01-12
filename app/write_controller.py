import logging

logger = logging.getLogger("control")

class WriteController:
    def __init__(self, gateway):
        self.gateway = gateway

    async def set_fish_type(self, code: str) -> bool:
        """將魚種代碼寫入 PLC"""
        logger.info(f"Request to set fish type: {code}")
        
        if not code or len(code) != 4:
            logger.warning("Invalid code length")
            return False

        # SimGateway 模式
        if hasattr(self.gateway, 'update_tag') and not hasattr(self.gateway, 'client'):
            self.gateway.update_tag('fish_code', code)
            return True

        # RealGateway 模式
        try:
            # [修改] 從 config 取得寫入地址
            # 注意: 這裡假設 read 和 write 是同一個地址 (通常設定值是這樣)
            # 需透過 gateway 存取 config
            start_addr = self.gateway.config['plc']['registers']['map']['fish_code']
            
            # "F001" -> 0x4630, 0x3031
            b = code.encode('ascii')
            val1 = (b[0] << 8) | b[1]
            val2 = (b[2] << 8) | b[3]
            
            # 連續寫入兩個暫存器
            res1 = await self.gateway.client.write_register(start_addr, val1)
            res2 = await self.gateway.client.write_register(start_addr + 1, val2)
            
            return res1 and res2
        except Exception as e:
            logger.error(f"Write failed: {e}")
            return False