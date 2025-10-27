import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/mudae.db")
OUTPUT_PATH = Path("data/series.db")
TOP_LIMIT = 1000  # use top 1000 meta-ranked characters

def build_series_rank():
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query("""
        SELECT
            name_display AS name,
            series_display AS series,
            COALESCE(claim_rank, 9999) AS claim_rank,
            COALESCE(like_rank, 9999) AS like_rank
        FROM characters
        WHERE series_display IS NOT NULL AND TRIM(series_display) != ''
        ORDER BY (COALESCE(claim_rank, 9999) + COALESCE(like_rank, 9999)) / 2 ASC
        LIMIT ?
    """, conn, params=(TOP_LIMIT,))

    conn.close()

    print(f"[✅] Loaded {len(df)} characters from mudae.db")

    # Compute meta rank
    df["meta_rank"] = (df["claim_rank"] + df["like_rank"]) / 2

    # Group by series
    grouped = (
        df.groupby("series")
          .agg(
              avg_meta_rank=("meta_rank", "mean"),
              characters_in_top=("name", "count")
          )
          .reset_index()
    )

    # Compute series score (weighted by representation and rank)
    grouped["series_score"] = grouped["characters_in_top"] * 10000 / (grouped["avg_meta_rank"] + 100)

    # Normalize
    max_score = grouped["series_score"].max()
    grouped["tier_score"] = (grouped["series_score"] / max_score) * 100

    # Assign tier
    def get_tier(score):
        if score >= 90: return "S"
        elif score >= 75: return "A"
        elif score >= 60: return "B"
        elif score >= 40: return "C"
        else: return "D"

    grouped["tier"] = grouped["tier_score"].apply(get_tier)

    # Sort by score descending for display
    grouped = grouped.sort_values("series_score", ascending=False).reset_index(drop=True)

    # Save
    conn_out = sqlite3.connect(OUTPUT_PATH)
    grouped.to_sql("series_rank", conn_out, if_exists="replace", index=False)
    conn_out.close()

    print(f"[💾] Saved {len(grouped)} series entries to {OUTPUT_PATH}")
    print("[📊] Top 10 Series by score:")
    print(grouped.head(10))

if __name__ == "__main__":
    build_series_rank()
