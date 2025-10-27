"""DB helper for upserting character info parsed from $im commands."""

import aiosqlite
from bot.db.database import get_conn

async def upsert_character_from_im(name_display, series_display, kakera_value=None,
                                   claim_rank=None, like_rank=None, data_source='organic'):
    conn = await get_conn()
    await conn.execute('''
        INSERT INTO characters (name_display, series_display, kakera_value, claim_rank, like_rank, data_source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(name_display) DO UPDATE SET
            series_display=excluded.series_display,
            kakera_value=excluded.kakera_value,
            claim_rank=excluded.claim_rank,
            like_rank=excluded.like_rank,
            data_source=excluded.data_source,
            last_updated=CURRENT_TIMESTAMP;
    ''', (name_display, series_display, kakera_value, claim_rank, like_rank, data_source))
    await conn.commit()
    await conn.close()
