import sqlite3
import math
import logging
from pathlib import Path
from typing import Optional, Dict, List

# ============================================================
# 📦 Database paths
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[3] if "src" in str(Path.cwd()) else Path.cwd()
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SERIES_DB_PATH = DATA_DIR / "series.db"
MUDAE_DB_PATH = DATA_DIR / "mudae.db"

# ============================================================
# 🧩 Logging setup
# ============================================================
logger = logging.getLogger("mudae-helper.series-rank")
logger.setLevel(logging.INFO)

# ============================================================
# 🧮 Utility functions
# ============================================================

def connect_series_db():
    return sqlite3.connect(SERIES_DB_PATH)

def connect_mudae_db():
    return sqlite3.connect(MUDAE_DB_PATH)

# ============================================================
# 🎯 Series rank computation (meta-based)
# ============================================================

def build_series_rank(top_limit: int = 1000):
    """
    Build series ranking from mudae.db (using top characters).
    Scoring emphasizes both high ranks and consistent presence.
    """
    import pandas as pd

    logger.info(f"[⚙️] Building series ranking from top {top_limit} characters...")

    with connect_mudae_db() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                name_display,
                series_display AS series,
                COALESCE(claim_rank, 9999) AS claim_rank,
                COALESCE(like_rank, 9999) AS like_rank
            FROM characters
            WHERE series IS NOT NULL
              AND TRIM(series) != ''
              AND claim_rank IS NOT NULL
              AND like_rank IS NOT NULL
            ORDER BY (COALESCE(claim_rank, 9999) + COALESCE(like_rank, 9999)) / 2 ASC
            LIMIT ?;
            """,
            conn,
            params=(top_limit,),
        )

    if df.empty:
        logger.warning("⚠️ No valid data in mudae.db → skipping series rank build.")
        return

    # Compute meta rank per character
    df["meta_rank"] = (df["claim_rank"] + df["like_rank"]) / 2

    # Group by series
    grouped = df.groupby("series").agg(
        avg_meta_rank=("meta_rank", "mean"),
        characters_in_top=("name_display", "count"),
    ).reset_index()

    # ============================================================
    # 🧠 Improved scoring formula (balanced influence)
    # ============================================================
    grouped["series_score"] = (
        (1 / grouped["avg_meta_rank"]) * 5e4 +
        (grouped["characters_in_top"] ** 1.5 * 250)
    )

    # Normalize to 0–100 range
    min_score = grouped["series_score"].min()
    max_score = grouped["series_score"].max()
    grouped["tier_score"] = 100 * (grouped["series_score"] - min_score) / (max_score - min_score)

    # ============================================================
    # 🧩 Dynamic tier assignment using quantiles
    # ============================================================
    quantiles = grouped["tier_score"].quantile([0.90, 0.75, 0.50, 0.25])
    def assign_tier(score):
        if score >= quantiles[0.90]:
            return "S"
        elif score >= quantiles[0.75]:
            return "A"
        elif score >= quantiles[0.50]:
            return "B"
        elif score >= quantiles[0.25]:
            return "C"
        else:
            return "D"

    grouped["tier"] = grouped["tier_score"].apply(assign_tier)

    # ============================================================
    # 💾 Save to series.db
    # ============================================================
    with connect_series_db() as conn:
        conn.execute("DROP TABLE IF EXISTS series_rank")
        grouped.to_sql("series_rank", conn, index=False)

    logger.info(f"[✅] Series ranking generated with {len(grouped)} entries.")
    logger.info(f"[💾] Saved to {SERIES_DB_PATH}")

    # ============================================================
    # 📊 Tier distribution summary
    # ============================================================
    tier_counts = grouped["tier"].value_counts().to_dict()
    print("\n[📈] Tier Distribution:")
    for tier, count in tier_counts.items():
        print(f"  {tier}: {count} series")

    # ============================================================
    # 🔝 Preview top 10
    # ============================================================
    top10 = grouped.sort_values("series_score", ascending=False).head(10)
    print("\n[📊] Top 10 Series by Score:")
    print(top10[["series", "avg_meta_rank", "characters_in_top", "series_score", "tier_score", "tier"]].to_string(index=False))

# ============================================================
# 🔍 Query helpers
# ============================================================

def get_series_info(series_name: str) -> Optional[Dict]:
    if not SERIES_DB_PATH.exists():
        logger.warning("⚠️ series.db not found.")
        return None

    conn = connect_series_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT series, avg_meta_rank, characters_in_top, series_score, tier_score, tier
        FROM series_rank
        WHERE LOWER(series) = LOWER(?)
        LIMIT 1;
        """,
        (series_name.strip(),),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_top_series(limit: int = 10) -> List[Dict]:
    if not SERIES_DB_PATH.exists():
        logger.warning("⚠️ series.db not found.")
        return []
    conn = connect_series_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT series, avg_meta_rank, characters_in_top, series_score, tier_score, tier
        FROM series_rank
        ORDER BY series_score DESC
        LIMIT ?;
        """,
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def tier_flavor_label(tier: str) -> str:
    mapping = {
        "S": "🌟 **S-TIER Series!** 🌟",
        "A": "🔥 **A-TIER Series!** 🔥",
        "B": "⭐ **B-TIER Series** ⭐",
        "C": "✨ **C-TIER Series** ✨",
        "D": "💤 **D-TIER Series** 💤",
    }
    return mapping.get(tier.upper(), "❔ **Unknown Tier** ❔")


def should_dm_user(meta_rank: Optional[float], kakera_value: Optional[float], series_score: Optional[float]) -> bool:
    if series_score is None or series_score <= 5:
        return False
    meta_ok = meta_rank is not None and meta_rank <= 5000
    kakera_ok = kakera_value is not None and kakera_value >= 100
    return meta_ok or kakera_ok


# ============================================================
# 🧪 CLI Test
# ============================================================
if __name__ == "__main__":
    print("[🧩] Rebuilding series rank...")
    build_series_rank()
    print("\n[🔍] Sample Query:")
    info = get_series_info("hololive")
    print(info or "Not found")
