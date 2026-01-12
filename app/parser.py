import struct
from typing import List, Dict, Any

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
                return struct.unpack('>I', raw)[0] # 使用 Unsigned Int
            return 0

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
                data['weight'] = parse_dword(self.map['weight_now']) / 100.0 # 假設有小數點 2 位
                # 若無小數點請改為: data['weight'] = parse_dword(self.map['weight_now'])

            if 'start_time_year' in self.map:
                data['start_time'] = parse_time(self.map['start_time_year'])

            if 'fish_code' in self.map:
                idx = get_idx(self.map['fish_code'])
                if 0 <= idx < len(registers) - 1:
                    raw = struct.pack('>HH', registers[idx], registers[idx+1])
                    code = raw.decode('ascii', errors='ignore').strip('\x00').strip()
                    data['fish_code'] = code if code else '----'

            # 2. 分規設定值讀取 (回讀目前設定)
            # 根據 PLC 表格邏輯解析
            if 'bucket_settings_start' in self.map:
                base = self.map['bucket_settings_start'] # 40101
                
                # Bucket 1: Min(40101), Max(40103), Target(40105)
                data['cfg_b1_min'] = parse_dword(base)
                data['cfg_b1_max'] = parse_dword(base + 2)
                data['cfg_b1_target'] = parse_dword(base + 4)
                
                # Bucket 2~7: Max, Target (Offset starts from 40107)
                # 40107 = base + 6
                current_addr = base + 6
                for i in range(2, 8):
                    data[f'cfg_b{i}_max'] = parse_dword(current_addr)
                    data[f'cfg_b{i}_target'] = parse_dword(current_addr + 2)
                    current_addr += 4

            # 3. 分規唯讀最小值 (Bucket 2~7)
            if 'bucket_ro_min_start' in self.map:
                base_ro = self.map['bucket_ro_min_start'] # 40043
                for i in range(2, 8):
                    addr = base_ro + (i-2)*2
                    data[f'cfg_b{i}_min'] = parse_dword(addr)

        except Exception as e:
            # pass or log error
            pass

        return data