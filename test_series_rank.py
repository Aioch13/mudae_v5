"""
setup_create_test_series_rank.py — auto-creates test_series_rank.py
Use once to fix incorrect file location or path issues.
"""

from pathlib import Path

# Target path
target_path = Path("src/tools/test_series_rank.py")
target_path.parent.mkdir(parents=True, exist_ok=True)

content = """\"\"\"
test_series_rank.py — Diagnostic tool for validating series ranking logic.

Usage:
    python src/tools/test_series_rank.py
\"\"\"

import sys
from pathlib import Path
import asyncio

# -------------------------------------------------------------------
# Ensure the project root (src/) is importable when running this file
# -------------------------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parents[1]))

# -------------------------------------------------------------------
# Imports from the bot package
# -------------------------------------------------------------------
from bot.db.series_rank import get_series_rankings, get_series_avg_rank


# -------------------------------------------------------------------
# MAIN TEST SCRIPT
# -------------------------------------------------------------------
async def main():
    print("📊 Generating Top 20 Series Rankings...\\n")

    try:
        results = await get_series_rankings(limit=20)
    except Exception as e:
        print(f"❌ Error fetching rankings: {e}")
        return

    if not results:
        print("⚠️ No series data found. Check your database or imported character data.")
        return

    for r in results:
        rank = r.get("rank", "?")
        tier = r.get("tier", "?")
        name = r.get("series_display", "Unknown")
        avg_rank = r.get("avg_meta_rank", 0)
        count = r.get("char_count", 0)
        print(f"#{rank:<3} [{tier:<10}] {name:<40} → avg rank {avg_rank:.2f} ({count} chars)")

    # Optional single-series lookup
    print("\\n🔍 Checking a single example:")
    target_series = "DARLING in the FRANXX"
    avg = await get_series_avg_rank(target_series)
    if avg:
        print(f"   {target_series} has an average meta rank ≈ {avg:.2f}")
    else:
        print(f"   {target_series} not found in database.")

    print("\\n✅ Series ranking test complete.")


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
"""

# Write file
target_path.write_text(content, encoding="utf-8")

print(f"✅ Created {target_path.resolve()}")
print("Now run:")
print("   python src/tools/test_series_rank.py")
