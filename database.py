import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "clinic.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not DB_PATH.exists():
        conn = get_conn()
        with open(Path(__file__).parent / "schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
