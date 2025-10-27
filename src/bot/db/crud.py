# src/bot/db/crud.py
import aiosqlite
import logging
from typing import Optional

from src.bot.db.database import get_conn
from src.bot.utils.normalization import normalize_text

logger = logging.getLogger("mudae-helper.db.crud")


# ============================================================
# UPSERT for $top imports
# ============================================================
async def upsert_character(
    name_display: str,
    series_display: str = "",
    kakera_value: Optional[int] = None,
    claim_rank: Optional[int] = None,
    like_rank: Optional[int] = None,
    data_source: str = "top",
) -> None:
    """
    Upsert for imported characters (e.g., from $top files).
    Matches strictly on name_normalized only.
    """
    name_norm = normalize_text(name_display)

    if not name_norm:
        logger.warning("Skipping upsert: empty normalized name")
        return

    sql = """
    INSERT INTO characters (
        name_display, name_normalized, series_display,
        kakera_value, claim_rank, like_rank, times_seen, data_source
    )
    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ON CONFLICT(name_normalized)
    DO UPDATE SET
        name_display = excluded.name_display,
        series_display = COALESCE(NULLIF(excluded.series_display, ''), characters.series_display),
        kakera_value = CASE
            WHEN excluded.kakera_value IS NOT NULL
                 AND (characters.kakera_value IS NULL OR excluded.kakera_value > characters.kakera_value)
            THEN excluded.kakera_value
            ELSE characters.kakera_value END,
        claim_rank = COALESCE(excluded.claim_rank, characters.claim_rank),
        like_rank  = COALESCE(excluded.like_rank, characters.like_rank),
        times_seen = characters.times_seen + 1,
        data_source = excluded.data_source,
        last_updated = CURRENT_TIMESTAMP;
    """

    try:
        conn = await get_conn()
        await conn.execute(
            sql,
            (
                name_display,
                name_norm,
                series_display,
                kakera_value,
                claim_rank,
                like_rank,
                data_source,
            ),
        )
        await conn.commit()
        await conn.close()
        logger.debug(f"Upserted (TOP): {name_display} | {series_display}")
    except Exception as e:
        logger.error(f"DB error in upsert_character: {e}")


# ============================================================
# UPSERT for $im updates (overwrites most recent info)
# ============================================================
async def upsert_character_from_im(
    name_display: str,
    series_display: str,
    kakera_value: Optional[int],
    claim_rank: Optional[int],
    like_rank: Optional[int],
) -> str:
    """
    Overwrites or inserts by name_normalized only.
    Returns "new", "update", or "skip" for logging.
    """
    name_norm = normalize_text(name_display)

    if not name_norm:
        logger.warning("Skipping IM upsert: empty normalized name")
        return "skip"

    conn = await get_conn()

    # Check existence by normalized name only
    cursor = await conn.execute(
        "SELECT id FROM characters WHERE name_normalized = ?;",
        (name_norm,),
    )
    existing = await cursor.fetchone()

    sql = """
    INSERT INTO characters (
        name_display, name_normalized, series_display,
        kakera_value, claim_rank, like_rank, times_seen, data_source
    )
    VALUES (?, ?, ?, ?, ?, ?, 1, 'im')
    ON CONFLICT(name_normalized)
    DO UPDATE SET
        name_display = excluded.name_display,
        series_display = excluded.series_display,
        kakera_value = excluded.kakera_value,
        claim_rank = excluded.claim_rank,
        like_rank = excluded.like_rank,
        times_seen = characters.times_seen + 1,
        data_source = 'im',
        last_updated = CURRENT_TIMESTAMP;
    """

    await conn.execute(
        sql,
        (
            name_display,
            name_norm,
            series_display,
            kakera_value,
            claim_rank,
            like_rank,
        ),
    )
    await conn.commit()
    await conn.close()

    # Return clear status for external logging
    if existing:
        return "update"
    else:
        return "new"
# ============================================================
# READ-ONLY FETCH for rolls (no overwriting)
# ============================================================
async def get_character_info(name_display: str, series_display: str) -> Optional[dict]:
    """
    Fetch existing character data by normalized name + series (case-insensitive).
    Used by the roll handler — never writes or updates.
    """
    from src.bot.utils.normalization import normalize_text
    name_norm = normalize_text(name_display or "")

    if not name_norm:
        logger.debug(f"[SKIP] Empty name for get_character_info({name_display}, {series_display})")
        return None

    conn = await get_conn()
    cursor = await conn.execute(
        """
        SELECT name_display, series_display, kakera_value, claim_rank, like_rank
        FROM characters
        WHERE name_normalized = ? AND LOWER(series_display) = LOWER(?)
        LIMIT 1;
        """,
        (name_norm, (series_display or "").lower()),
    )
    row = await cursor.fetchone()
    await conn.close()

    if not row:
        logger.debug(f"[MISS] Character not found in DB: {name_display} | {series_display}")
        return None

    return {
        "name_display": row[0],
        "series_display": row[1],
        "kakera_value": row[2],
        "claim_rank": row[3],
        "like_rank": row[4],
    }

# ============================================================
# READ helper — get character info from DB (by name)
# ============================================================
async def get_character_info(name_display: str, series_display: str):
    """
    Lookup existing character info by normalized name (case-insensitive).
    Returns dict with kakera_value, claim_rank, like_rank, and computed meta_rank.
    """
    name_norm = normalize_text(name_display)
    if not name_norm:
        return None

    conn = await get_conn()
    conn.row_factory = aiosqlite.Row
    cursor = await conn.execute(
        """
        SELECT name_display, series_display, kakera_value,
               claim_rank, like_rank,
               CASE
                   WHEN claim_rank IS NOT NULL AND like_rank IS NOT NULL
                        THEN (claim_rank + like_rank) / 2.0
                   WHEN claim_rank IS NOT NULL THEN claim_rank
                   WHEN like_rank  IS NOT NULL THEN like_rank
                   ELSE NULL
               END AS meta_rank
        FROM characters
        WHERE name_normalized = ?
        LIMIT 1;
        """,
        (name_norm,),
    )
    row = await cursor.fetchone()
    await conn.close()

    return dict(row) if row else None
