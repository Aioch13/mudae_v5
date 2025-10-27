# test_im_update.py
import asyncio
import sys
from pathlib import Path

# Add src/ to path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from bot.db.crud import upsert_character_from_im

async def test_im():
    await upsert_character_from_im(
        name_display="Zero Two",
        series_display="DARLING in the FRANXX",
        kakera_value=1200,
        claim_rank=2,
        like_rank=4
    )
    print("✅ $im test update complete")

if __name__ == "__main__":
    asyncio.run(test_im())
    