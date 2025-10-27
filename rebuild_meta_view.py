import sqlite3
from pathlib import Path

db_path = Path("data/mudae.db")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DROP VIEW IF EXISTS characters_meta")

# ✅ Final version — no 'source', no 'last_update'
cur.execute("""
CREATE VIEW characters_meta AS
SELECT
    id,
    name_display,
    series_display,
    kakera_value,
    claim_rank,
    like_rank,
    ((COALESCE(claim_rank, 9999) + COALESCE(like_rank, 9999)) / 2.0) AS meta_rank
FROM characters
WHERE name_display IS NOT NULL
  AND TRIM(name_display) != '';
""")

conn.commit()
conn.close()
print("✅ Recreated characters_meta view successfully (no 'last_update' or 'source' columns used).")
