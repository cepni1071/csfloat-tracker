import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_hash_name TEXT NOT NULL,
            target_price REAL,
            last_price REAL,
            float_min REAL DEFAULT 0.0,
            float_max REAL DEFAULT 1.0,
            image_url TEXT,
            global_price REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(market_hash_name, float_min, float_max)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skin_id INTEGER,
            price REAL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (skin_id) REFERENCES skins(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_all_skins():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, market_hash_name, target_price, last_price,
               float_min, float_max, image_url, global_price
        FROM skins ORDER BY market_hash_name
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def add_skin(market_hash_name, target_price=None, float_min=0.0, float_max=1.0, image_url=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO skins (market_hash_name, target_price, float_min, float_max, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (market_hash_name, target_price, float_min, float_max, image_url))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_skin(skin_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM price_history WHERE skin_id = ?", (skin_id,))
    c.execute("DELETE FROM skins WHERE id = ?", (skin_id,))
    conn.commit()
    conn.close()

def update_last_price(skin_id, price, global_price=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE skins SET last_price = ?, global_price = COALESCE(?, global_price) WHERE id = ?",
              (price, global_price, skin_id))
    c.execute("INSERT INTO price_history (skin_id, price) VALUES (?, ?)", (skin_id, price))
    conn.commit()
    conn.close()

def update_target_price(skin_id, target_price):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE skins SET target_price = ? WHERE id = ?", (target_price, skin_id))
    conn.commit()
    conn.close()
