import sqlite3
import logging
import os
import json
from contextlib import contextmanager
from typing import Optional, Dict, List
from datetime import datetime, timedelta

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

                # 3. 分規配方表
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

    def log_data(self, data: dict):
        """寫入一筆歷史資料 (Time, FishCode, Weight, Status)"""
        try:
            # [修正] 使用 Python 的 datetime.now() 取得系統當前時間 (Local Time)
            # 這能避免 SQLite DEFAULT CURRENT_TIMESTAMP 使用 UTC 導致的時間差
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                # 明確寫入 timestamp 欄位
                conn.execute('INSERT INTO history (timestamp, fish_code, weight, status) VALUES (?, ?, ?, ?)',
                           (current_time, data.get('fish_code'), data.get('weight'), data.get('status')))
            # logger.debug("Data logged successfully to DB")
        except Exception as e: 
            logger.error(f"Log data failed: {e}")

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
        except Exception as e:
            logger.error(f"Get history failed: {e}")
            return []

    def get_daily_stats(self):
        """
        統計「今日」各魚種的生產數量
        """
        try:
            today_start = datetime.now().strftime('%Y-%m-%d 00:00:00')
            
            with self.get_connection() as conn:
                sql = '''
                    SELECT 
                        h.fish_code,
                        COALESCE(f.name, h.fish_code) as name,
                        COUNT(*) as count
                    FROM history h
                    LEFT JOIN fish_type f ON h.fish_code = f.code
                    WHERE h.timestamp >= ?
                    GROUP BY h.fish_code
                '''
                rows = conn.execute(sql, (today_start,)).fetchall()
                
                labels = []
                data = []
                
                for r in rows:
                    labels.append(r['name'])
                    data.append(r['count'])
                
                return {"labels": labels, "data": data}
                
        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {"labels": [], "data": []}

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

    def save_recipe(self, fish_code: str, params: dict) -> bool:
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
        try:
            with self.get_connection() as conn:
                row = conn.execute('SELECT params FROM fish_recipes WHERE fish_code = ?', (fish_code,)).fetchone()
                if row:
                    return json.loads(row['params'])
                return {}
        except Exception as e:
            logger.error(f"Get recipe failed: {e}")
            return {}