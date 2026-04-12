import sqlite3

def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        run_id TEXT,
        canal TEXT,
        titulo TEXT,
        sentimiento TEXT,
        score REAL,
        resumen TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_video(user, run_id, canal, titulo, sentimiento, score, resumen):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO videos (user, run_id, canal, titulo, sentimiento, score, resumen)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user, run_id, canal, titulo, sentimiento, score, resumen))

    conn.commit()
    conn.close()