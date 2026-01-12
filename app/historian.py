import sqlite3
import logging
import os
import json
from contextlib import contextmanager
from typing import Optional, Dict, List

logger = logging.getLogger("historian")

class Historian:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn: conn.close()

    def init_db(self):
        try:
            with self.get_connection() as conn:
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
                
                # Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_ts ON history(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_code ON history(fish_code)')

                # 2. 魚種對應表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fish_type (
                        code TEXT PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                ''')

                # [新增] 3. 分規配方表 (Recipe)
                # 儲存每個魚種對應的分規參數 (JSON 格式儲存以保留彈性)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fish_recipes (
                        fish_code TEXT PRIMARY KEY,
                        params JSON,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"DB Init failed: {e}")
            raise

    # ... (原有 log_data, get_history_data 等維持不變) ...

    def log_data(self, data: dict):
        try:
            with self.get_connection() as conn:
                conn.execute('INSERT INTO history (fish_code, weight, status) VALUES (?, ?, ?)',
                           (data.get('fish_code'), data.get('weight'), data.get('status')))
        except Exception as e: logger.error(f"Log data failed: {e}")

    def get_history_data(self, start_time=None, end_time=None, fish_code=None, limit=1000):
        try:
            with self.get_connection() as conn:
                q = 'SELECT * FROM history WHERE 1=1'
                p = []
                if start_time: q += ' AND timestamp >= ?'; p.append(start_time)
                if end_time: q += ' AND timestamp <= ?'; p.append(end_time)
                if fish_code: q += ' AND fish_code = ?'; p.append(fish_code)
                q += ' ORDER BY timestamp DESC LIMIT ?'; p.append(limit)
                cursor = conn.execute(q, p)
                return [dict(r) for r in cursor.fetchall()]
        except Exception: return []

    def get_daily_stats(self):
        # Mock data for dashboard
        return {"labels": ["白鯧", "鮭魚", "鮪魚", "吳郭魚"], "data": [12, 5, 8, 15]}

    def get_all_fish_types(self) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute('SELECT code, name FROM fish_type ORDER BY code ASC').fetchall()
                return [dict(r) for r in rows]
        except Exception: return []

    def upsert_fish_type(self, code: str, name: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute('INSERT OR REPLACE INTO fish_type (code, name) VALUES (?, ?)', (code, name))
                return True
        except Exception: return False

    def delete_fish_type(self, code: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM fish_type WHERE code = ?', (code,))
                return True
        except Exception: return False

    # [新增] 配方 CRUD
    def save_recipe(self, fish_code: str, params: dict) -> bool:
        """儲存分規設定到資料庫"""
        try:
            json_str = json.dumps(params)
            with self.get_connection() as conn:
                conn.execute('INSERT OR REPLACE INTO fish_recipes (fish_code, params) VALUES (?, ?)', 
                           (fish_code, json_str))
                return True
        except Exception as e:
            logger.error(f"Save recipe failed: {e}")
            return False

    def get_recipe(self, fish_code: str) -> Dict:
        """讀取分規設定"""
        try:
            with self.get_connection() as conn:
                row = conn.execute('SELECT params FROM fish_recipes WHERE fish_code = ?', (fish_code,)).fetchone()
                if row:
                    return json.loads(row['params'])
                return {}
        except Exception as e:
            logger.error(f"Get recipe failed: {e}")
            return {}