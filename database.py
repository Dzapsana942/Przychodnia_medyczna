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
def get_doctor_schedule(doctor_id):
    conn = sqlite3.connect("clinic.db")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT day_of_week, start_time, end_time
        FROM doctor_schedule
        WHERE doctor_id = ?
        """,
        (doctor_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def add_schedule(doctor_id: int, day_of_week: int, start_time: str, end_time: str):
    """
    Dodaje nowy wpis grafiku dla lekarza
    day_of_week: 1=Poniedziałek ... 5=Piątek
    start_time / end_time: w formacie "HH:MM"
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO doctor_schedule (doctor_id, day_of_week, start_time, end_time)
        VALUES (?, ?, ?, ?)
        """,
        (doctor_id, day_of_week, start_time, end_time)
    )
    conn.commit()
    conn.close()
