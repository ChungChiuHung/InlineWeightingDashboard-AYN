from typing import List, Dict, Any
import struct
import logging

logger = logging.getLogger("parser")

class TagParser:
    def __init__(self, addr_map: dict):
        """
        初始化 Parser
        :param addr_map: 從 config 傳入的地址對應表 {'fish_code': 40131, ...}
        """
        self.map = addr_map

    def parse_block(self, registers: List[int], start_address: int) -> Dict[str, Any]:
        data = {}
        if not registers:
            return data

        # Helper: 計算某個 Modbus 地址在 registers 陣列中的 index
        def get_idx(target_addr):
            return target_addr - start_address

        try:
            # 1. 解析魚種代碼 (String, 2 words)
            addr = self.map.get('fish_code')
            if addr:
                idx = get_idx(addr)
                # 確保不會超出陣列範圍
                if 0 <= idx < len(registers) - 1:
                    raw = struct.pack('>HH', registers[idx], registers[idx+1])
                    code = raw.decode('ascii', errors='ignore').strip('\x00').strip()
                    data['fish_code'] = code if code else '----'

            # 2. 解析重量 (Float32, 2 words)
            addr = self.map.get('weight')
            if addr:
                idx = get_idx(addr)
                if 0 <= idx < len(registers) - 1:
                    raw = struct.pack('>HH', registers[idx], registers[idx+1])
                    weight = struct.unpack('>f', raw)[0]
                    data['weight'] = round(weight, 2)

            # 3. 解析狀態 (Int, 1 word)
            addr = self.map.get('status')
            if addr:
                idx = get_idx(addr)
                if 0 <= idx < len(registers):
                    val = registers[idx]
                    if val == 1:
                        data['status'] = 'RUN'
                    elif val == 2:
                        data['status'] = 'ALARM'
                    else:
                        data['status'] = 'IDLE'

        except Exception as e:
            logger.error(f"Parsing error: {e}")

        return data