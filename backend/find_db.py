import os
import sqlite3

DB_PATH = os.getenv('DB_PATH', '/app/data/encuestas.db')
print(f"DB_PATH environment variable: {os.getenv('DB_PATH')}")
print(f"Effective DB_PATH: {DB_PATH}")
print(f"Absolute Effective DB_PATH: {os.path.abspath(DB_PATH)}")
print(f"Exists: {os.path.exists(DB_PATH)}")

# Try to find any other sqlite files in common places
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db') or file.endswith('.sqlite'):
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            print(f"Found DB: {path} (Size: {size})")
