import sqlite3
from pathlib import Path

db_path = Path("data/mudae.db")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List all views to find any that depend on characters_old
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
views = cur.fetchall()
for name, sql in views:
    print(f"View found: {name}\n{sql}\n")

# Drop any view that mentions characters_old
for name, sql in views:
    if "characters_old" in (sql or ""):
        print(f"Dropping broken view: {name}")
        cur.execute(f"DROP VIEW IF EXISTS {name}")

conn.commit()
conn.close()
print("✅ Cleaned up all broken views referencing characters_old.")
