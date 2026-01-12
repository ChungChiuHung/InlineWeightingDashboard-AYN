import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger("historian")

class Historian:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 確保目錄存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def init_db(self):
        """初始化資料庫表結構"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 建立歷史記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    fish_code TEXT,
                    weight REAL,
                    status TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"DB Init failed: {e}")

    def log_data(self, data: dict):
        """寫入一筆資料"""
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

    def get_daily_stats(self):
        """取得今日產量統計 (供圓餅圖使用)"""
        # 範例實作：回傳假資料或查詢 DB
        # 在原型階段，先回傳固定格式讓前端能跑
        return {
            "labels": ["白鯧", "鮭魚", "鮪魚", "吳郭魚"],
            "data": [12, 5, 8, 15]
        }