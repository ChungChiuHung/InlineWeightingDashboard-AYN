import sqlite3
import time
from collections import defaultdict

class Historian:
    def __init__(self, db_path, flush_interval=1.0, tag_whitelist=None, status=None):
        self.db_path = db_path
        self.flush_interval = flush_interval
        self.tag_whitelist = set(tag_whitelist or [])
        self.buffer = defaultdict(list)
        self.last_value = {}
        self.last_flush = time.time()
        self._init_db()
        self.status = status

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            ts INTEGER,
            tag TEXT,
            avg REAL,
            min REAL,
            max REAL,
            last REAL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_tag_ts
        ON history(tag, ts)
        """)
        conn.commit()
        conn.close()

    def push(self, tag, value, ts):
        if self.tag_whitelist and tag not in self.tag_whitelist:
            return

        self.buffer[tag].append(value)
        self.last_value[tag] = value

        now = time.time()
        if now - self.last_flush >= self.flush_interval:
            self.flush(int(now))

    def flush(self, ts):
        if not self.buffer:
            return

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for tag, values in self.buffer.items():
            cur.execute(
                "INSERT INTO history (ts, tag, avg, min, max, last) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    ts,
                    tag,
                    sum(values) / len(values),
                    min(values),
                    max(values),
                    self.last_value.get(tag)
                )
            )

        conn.commit()
        conn.close()
        self.buffer.clear()
        self.last_flush = time.time()
        if self.status:
            self.status.mark_flush()
