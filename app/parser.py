import struct
import logging
from typing import List, Dict, Any

# 設定 Logger
logger = logging.getLogger("parser")

class TagParser:
    def __init__(self, addr_map: dict):
        self.map = addr_map

    def parse_block(self, registers: List[int], start_address: int) -> Dict[str, Any]:
        data = {}
        if not registers:
            return data

        def get_idx(target_addr):
            return target_addr - start_address

        # 解析 32-bit Dword (Big-Endian)
        def parse_dword(addr):
            idx = get_idx(addr)
            if 0 <= idx < len(registers) - 1:
                raw = struct.pack('>HH', registers[idx], registers[idx+1])
                val = struct.unpack('>I', raw)[0]
                return val
            return None # 修改：若索引越界回傳 None 以便區分

        # 解析時間
        def parse_time(start_addr):
            idx = get_idx(start_addr)
            if 0 <= idx <= len(registers) - 6:
                y, m, d, h, min_, s = registers[idx:idx+6]
                return f"{y}-{m:02d}-{d:02d} {h:02d}:{min_:02d}:{s:02d}"
            return "--"

        try:
            # 1. 基礎數據
            if 'weight_now' in self.map:
                val = parse_dword(self.map['weight_now'])
                if val is not None: data['weight'] = val

            if 'start_time_year' in self.map:
                data['start_time'] = parse_time(self.map['start_time_year'])

            if 'fish_code' in self.map:
                addr = self.map['fish_code']
                idx = get_idx(addr)
                if 0 <= idx < len(registers) - 1:
                    raw = struct.pack('>HH', registers[idx], registers[idx+1])
                    code = raw.decode('ascii', errors='ignore').strip('\x00').strip()
                    data['fish_code'] = code if code else '----'

            if 'status' in self.map:
                idx = get_idx(self.map['status'])
                if 0 <= idx < len(registers):
                    val = registers[idx]
                    status_map = {1: 'RUN', 2: 'IDLE', 3: 'ALARM', 4: 'STOP'}
                    data['status'] = status_map.get(val, 'UNKNOWN')

            # [新增] 2. 分規設定值讀取 (加強除錯)
            if 'bucket_settings_start' in self.map:
                base = self.map['bucket_settings_start'] # 40101
                
                # Bucket 1
                b1_min = parse_dword(base)
                b1_max = parse_dword(base + 2)
                b1_tgt = parse_dword(base + 4)
                
                if b1_min is not None: data['cfg_b1_min'] = b1_min
                if b1_max is not None: data['cfg_b1_max'] = b1_max
                if b1_tgt is not None: data['cfg_b1_target'] = b1_tgt
                
                # Bucket 2~7
                current_addr = base + 6
                for i in range(2, 8):
                    b_max = parse_dword(current_addr)
                    b_tgt = parse_dword(current_addr + 2)
                    
                    if b_max is not None: data[f'cfg_b{i}_max'] = b_max
                    if b_tgt is not None: data[f'cfg_b{i}_target'] = b_tgt
                    
                    current_addr += 4

            # [新增] 3. 分規唯讀最小值 (Bucket 2~7)
            if 'bucket_ro_min_start' in self.map:
                base_ro = self.map['bucket_ro_min_start'] # 40043
                for i in range(2, 8):
                    addr = base_ro + (i-2)*2
                    b_min = parse_dword(addr)
                    if b_min is not None: data[f'cfg_b{i}_min'] = b_min

        except Exception as e:
            logger.error(f"Parser Error: {e}", exc_info=True)
            pass

        return data