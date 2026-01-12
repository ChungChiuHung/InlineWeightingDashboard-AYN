import sqlite3
import logging
import os

logger = logging.getLogger("historian")

class Historian:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 確保資料夾存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def init_db(self):
        """初始化資料庫表結構"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 歷史記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    fish_code TEXT,
                    weight REAL,
                    status TEXT
                )
            ''')

            # 2. 魚種對應表 (Fish Type Mapping)
            # code: F001 (PLC只存這個，設為 Primary Key)
            # name: 白鯧 (UI顯示這個)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fish_type (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            ''')

            # 3. 預設資料 (種子數據)
            cursor.execute('SELECT count(*) FROM fish_type')
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding default fish types...")
                defaults = [
                    ('F001', '白鯧 (White Pomfret)'),
                    ('F002', '鮭魚 (Salmon)'),
                    ('F003', '鮪魚 (Tuna)'),
                    ('F004', '吳郭魚 (Tilapia)')
                ]
                cursor.executemany('INSERT OR IGNORE INTO fish_type (code, name) VALUES (?, ?)', defaults)

            conn.commit()
            conn.close()
            logger.info(f"Database initialized successfully at {self.db_path}")
        except Exception as e:
            logger.error(f"DB Init failed: {e}")

    def log_data(self, data: dict):
        """寫入歷史記錄"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (fish_code, weight, status)
                VALUES (?, ?, ?)
            ''', (data.get('fish_code'), data.get('weight'), data.get('status')))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Log data failed: {e}")

    # --- Fish Type CRUD Methods (修正儲存問題) ---

    def get_all_fish_types(self):
        """取得所有魚種設定"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row # 讓結果可以像字典一樣存取
            cursor = conn.cursor()
            cursor.execute('SELECT code, name FROM fish_type ORDER BY code ASC')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get fish types failed: {e}")
            return []

    def upsert_fish_type(self, code: str, name: str):
        """新增或更新魚種 (使用 INSERT OR REPLACE 確保覆寫)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 使用 INSERT OR REPLACE 語法，如果 code 存在就更新，不存在就新增
            cursor.execute('INSERT OR REPLACE INTO fish_type (code, name) VALUES (?, ?)', (code, name))
            conn.commit()
            conn.close()
            logger.info(f"Saved fish type: {code} -> {name}")
            return True
        except Exception as e:
            logger.error(f"Upsert fish type failed: {e}")
            return False

    def delete_fish_type(self, code: str):
        """刪除魚種"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM fish_type WHERE code = ?', (code,))
            conn.commit()
            conn.close()
            logger.info(f"Deleted fish type: {code}")
            return True
        except Exception as e:
            logger.error(f"Delete fish type failed: {e}")
            return False

    def get_daily_stats(self):
        """取得今日產量統計 (Mock data)"""
        return {
            "labels": ["白鯧", "鮭魚", "鮪魚", "吳郭魚"],
            "data": [12, 5, 8, 15]
        }