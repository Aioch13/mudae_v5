# ============================================================
# 📘 Mudae V3 Recommender System
# ============================================================
import sys
from pathlib import Path
import aiosqlite
import logging

# Ensure root path is importable
sys.path.append(str(Path(__file__).resolve().parents[2]))

from bot.db.database import get_conn
from bot.db.series_rank import get_top_series

logger = logging.getLogger("mudae-helper.recommendator")
logger.setLevel(logging.INFO)

# ============================================================
# 🧩 Top Character Recommendations
# ============================================================

async def recommend_top_characters(limit: int = 10):
    """
    Recommend globally top characters by lowest meta_rank.
    Falls back to highest kakera if meta ranks missing.
    """
    conn = await get_conn()

    query = """
    SELECT name_display, series_display, kakera_value, meta_rank
    FROM characters_meta
    WHERE meta_rank < 9999
    ORDER BY meta_rank ASC
    LIMIT ?;
    """
    cursor = await conn.execute(query, (limit,))
    chars = await cursor.fetchall()

    # If DB has no meta_rank yet, fallback to kakera_value
    if not chars:
        cursor = await conn.execute("""
            SELECT name_display, series_display, kakera_value, NULL
            FROM characters
            WHERE kakera_value IS NOT NULL
            ORDER BY kakera_value DESC
            LIMIT ?;
        """, (limit,))
        chars = await cursor.fetchall()

    await conn.close()

    results = [{
        "name": c[0],
        "series": c[1],
        "kakera": c[2],
        "meta_rank": c[3],
        "source": "meta_rank" if c[3] is not None else "kakera_value",
    } for c in chars]

    logger.info(f"[📊] Generated {len(results)} top character recommendations.")
    return results


# ============================================================
# 🧩 Series Popularity Recommendations
# ============================================================

async def recommend_popular_series(limit: int = 10):
    """
    Recommend top series by popularity score (from series.db).
    """
    series_list = get_top_series(limit=limit)

    if not series_list:
        logger.warning("⚠️ No series ranking data available.")
        return []

    results = [{
        "series": s["series"],
        "score": s["series_score"],
        "chars": s["characters_in_top"],
        "tier": s["tier"],
    } for s in series_list]

    logger.info(f"[📊] Generated {len(results)} top series recommendations.")
    return results


# ============================================================
# 🧠 Hybrid Recommender
# ============================================================

async def recommend(limit: int = 10):
    """
    Smart hybrid recommender:
      1️⃣ Prefer top characters (meta_rank)
      2️⃣ Fall back to top series (from series.db)
      3️⃣ Last resort: top kakera values
    """
    top_chars = await recommend_top_characters(limit=limit)

    # Fallback to series if not enough characters
    if not top_chars or len(top_chars) < 3:
        logger.warning("⚠️ Not enough characters — falling back to series popularity...")
        top_series = await recommend_popular_series(limit=limit)
        return [{
            "series": s["series"],
            "tier": s["tier"],
            "score": s["score"],
            "source": "series"
        } for s in top_series]

    return top_chars


# ============================================================
# 🧪 Quick CLI Test
# ============================================================
if __name__ == "__main__":
    import asyncio

    async def _test():
        print("[🧩] Fetching top characters...")
        chars = await recommend_top_characters(limit=5)
        for c in chars:
            print(f"- {c['name']} ({c['series']}) | meta_rank={c['meta_rank']} | kakera={c['kakera']}")

        print("\n[🧩] Fetching top series...")
        series = await recommend_popular_series(limit=5)
        for s in series:
            print(f"- {s['series']} | score={s['score']:.2f} | tier={s['tier']} | chars={s['chars']}")

    asyncio.run(_test())
