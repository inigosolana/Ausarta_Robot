import sqlite3
import os

DB_PATH = 'c:/Users/inigo2.solana/ausarta-robot-voice-agent-platform/backend/database.sqlite'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(encuestas)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Columns in encuestas: {columns}")

conn.close()
