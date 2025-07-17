import sqlite3
import threading
from contextlib import contextmanager
from config import DB_PATH

_lock = threading.Lock()

@contextmanager
def _conn():
    with _lock:
        con = sqlite3.connect(DB_PATH)
        try:
            yield con
        finally:
            con.close()

def _init():
    with _conn() as con:
        # таблица для очков гойды
        con.execute("""
            CREATE TABLE IF NOT EXISTS scores(
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                score INTEGER DEFAULT 0,
                PRIMARY KEY(chat_id, user_id)
            )
        """)
        # таблица для процента фембойности
        con.execute("""
            CREATE TABLE IF NOT EXISTS femboy(
                chat_id INTEGER,
                user_id INTEGER,
                percent INTEGER DEFAULT 0,
                PRIMARY KEY(chat_id, user_id)
            )
        """)
        con.commit()

def add_femboy(chat_id: int, user_id: int, delta: int):
    with _conn() as con:
        con.execute(
            "INSERT INTO femboy(chat_id,user_id,percent) VALUES(?,?,?) "
            "ON CONFLICT(chat_id,user_id) DO UPDATE SET "
            "percent = MIN(100, percent + excluded.percent)",
            (chat_id, user_id, delta)
        )
        con.commit()

def get_femboy(chat_id: int, user_id: int) -> int:
    with _conn() as con:
        cur = con.execute(
            "SELECT percent FROM femboy WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row[0] if row else 0

def add_score(chat_id: int, user_id: int, username: str, delta: int):
    with _conn() as con:
        con.execute(
            "INSERT INTO scores(chat_id, user_id, username, score) "
            "VALUES(?,?,?,?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET "
            "username=excluded.username, score=score+excluded.score",
            (chat_id, user_id, username, delta)
        )
        con.commit()

def get_top(chat_id: int, limit: int = 5):
    with _conn() as con:
        cur = con.execute(
            "SELECT username, score FROM scores "
            "WHERE chat_id=? "
            "ORDER BY score DESC LIMIT ?",
            (chat_id, limit)
        )
        return cur.fetchall()

def get_bottom(chat_id: int, limit: int = 5):
    with _conn() as con:
        cur = con.execute(
            "SELECT username, score FROM scores "
            "WHERE chat_id=? "
            "ORDER BY score ASC LIMIT ?",
            (chat_id, limit)
        )
        return cur.fetchall()

def get_user_score(chat_id: int, user_id: int) -> int:
    with _conn() as con:
        cur = con.execute(
            "SELECT score FROM scores WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row[0] if row else 0

def reset_scores(chat_id: int | None = None):
    with _conn() as con:
        if chat_id is None:
            con.execute("UPDATE scores SET score=0")
        else:
            con.execute("UPDATE scores SET score=0 WHERE chat_id=?", (chat_id,))
        con.commit()

def get_top_femboy(chat_id: int) -> tuple[int, int] | None:
    """Вернуть (user_id, percent) с самым высоким % в чате."""
    with _conn() as con:
        cur = con.execute(
            "SELECT user_id, percent FROM femboy "
            "WHERE chat_id=? ORDER BY percent DESC LIMIT 1",
            (chat_id,)
        )
        return cur.fetchone()

def reset_femboy(chat_id: int | None = None):
    """Сбросить всем процент фембойности (в чате или глобально)."""
    with _conn() as con:
        if chat_id is None:
            con.execute("UPDATE femboy SET percent=0")
        else:
            con.execute("UPDATE femboy SET percent=0 WHERE chat_id=?", (chat_id,))
        con.commit()
        
def _init():
    with _conn() as con:
        # … scores / femboy …
        con.execute("""
            CREATE TABLE IF NOT EXISTS femboy_winner(
                chat_id INTEGER PRIMARY KEY,
                win_date TEXT          -- YYYY-MM-DD когда объявлен
            )
        """)
        con.commit()

def set_femboy_winner(chat_id: int, date: str):
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO femboy_winner(chat_id, win_date) VALUES(?,?)",
            (chat_id, date)
        )
        con.commit()

def has_femboy_winner_today(chat_id: int, date: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "SELECT 1 FROM femboy_winner WHERE chat_id=? AND win_date=?",
            (chat_id, date)
        )
        return cur.fetchone() is not None

def clear_femboy_winners():
    with _conn() as con:
        con.execute("DELETE FROM femboy_winner")
        con.commit()

_init()
