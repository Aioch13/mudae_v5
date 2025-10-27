# src/bot/db/database.py
import aiosqlite
from pathlib import Path
import logging
import sys

# Ensure root path (Mudae_v3/src)
sys.path.append(str(Path(__file__).resolve().parents[2]))

from bot.config import DB_PATH  # ✅ fixed universal import

logger = logging.getLogger("mudae-helper.db")



# ------------------------------------------------------------
# Connection helper
# ------------------------------------------------------------
async def get_conn():
    """Return an async SQLite connection with safe PRAGMA settings."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")  # Better concurrency
    return conn


# ------------------------------------------------------------
# Database initialization
# ------------------------------------------------------------
async def init_db():
    """
    Ensure the database structure exists:
      - characters table
      - indexes on normalized fields
      - view for computed meta_rank
    """
    conn = await get_conn()

    await conn.executescript("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_display TEXT NOT NULL,
        name_normalized TEXT NOT NULL,
        series_display TEXT DEFAULT 'Unknown',
        series_normalized TEXT DEFAULT 'unknown',
        kakera_value INTEGER DEFAULT NULL,
        claim_rank INTEGER DEFAULT NULL,
        like_rank INTEGER DEFAULT NULL,
        times_seen INTEGER DEFAULT 1,
        data_source TEXT DEFAULT 'organic',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name_normalized, series_normalized)
    );

    CREATE INDEX IF NOT EXISTS idx_chars_name_norm ON characters(name_normalized);
    CREATE INDEX IF NOT EXISTS idx_chars_series_norm ON characters(series_normalized);
    """)

    # --- Create view for computed meta_rank ---
    await conn.executescript("""
    CREATE VIEW IF NOT EXISTS characters_meta AS
    SELECT *,
      CASE
        WHEN claim_rank IS NOT NULL AND like_rank IS NOT NULL
             THEN (claim_rank + like_rank) / 2.0
        WHEN claim_rank IS NOT NULL THEN claim_rank
        WHEN like_rank IS NOT NULL THEN like_rank
        ELSE 9999
      END AS meta_rank
    FROM characters;
    """)

    await conn.commit()
    await conn.close()
    logger.info("✅ Initialized DB: ensured tables and view exist.")
