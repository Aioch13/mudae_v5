# src/bot/scraper.py
import re
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.bot.db.crud import upsert_character
from src.bot.utils.normalization import normalize_text
from src.bot.config import DB_PATH  # used for context; not required in this file

logger = logging.getLogger("mudae-helper.scraper")

class TopListScraper:
    """
    v3 TopListScraper:
      - manual workflow supported: call start_scraping(ctx, list_type)
      - then human types $top <page> in the Mudae channel
      - owner runs scraper_page(page) or the on_message handler will detect page footers automatically
    """
    def __init__(self):
        self.scraping = False
        self.current_list: Optional[str] = None  # "claimed" or "liked"
        self.current_page = 0
        self.total_pages = 100  # default max pages to consider (configurable)
        self.collected_data: List[Dict] = []
        self.start_time: Optional[datetime] = None
        self.message_channel = None
        self.expected_manual_page: Optional[int] = None

    async def start_scraping(self, ctx, list_type: str = "claimed", total_pages: int = 67) -> bool:
        if self.scraping:
            await ctx.send("❌ Scraper already running.")
            return False

        self.scraping = True
        self.current_list = list_type
        self.current_page = 0
        self.total_pages = total_pages
        self.collected_data = []
        self.start_time = datetime.utcnow()
        self.message_channel = ctx.channel
        self.expected_manual_page = None
        await ctx.send(f"📡 Started scraper for `{list_type}`. Type `$top 1` in Mudae channel to begin (or use `$topl 1` for liked).")
        logger.info(f"Started TopListScraper for {list_type}, expecting up to {total_pages} pages.")
        return True

    async def process_top_embed(self, embed) -> bool:
        """
        Parse a top-list embed returned by Mudae and add entries.
        Returns True if parse succeeded for this embed.
        """
        try:
            # detect page from footer if present
            page = None
            if embed.footer and getattr(embed.footer, "text", None):
                m = re.search(r'(\d{1,3})\s*(?:/|of)\s*(\d{1,3})', embed.footer.text)
                if m:
                    page = int(m.group(1))
                    total = int(m.group(2))
                    self.total_pages = total

            # If expected_manual_page is set, require it to match (manual flow)
            if self.expected_manual_page is not None:
                if page is None or page != self.expected_manual_page:
                    logger.debug(f"Embed page {page} did not match expected manual page {self.expected_manual_page}; skipping.")
                    return False  # wait for the expected page
                # once matched, clear expectation so next manual page can be set
                self.expected_manual_page = None

            # Collect text sources in embed
            raw_text = []
            if embed.title:
                raw_text.append(embed.title)
            if embed.description:
                raw_text.append(embed.description)
            if getattr(embed, "fields", None):
                for f in embed.fields:
                    if f.name:
                        raw_text.append(f.name)
                    if f.value:
                        raw_text.append(f.value)
            joined = "\n".join(raw_text)

            # Normalize separators & split into lines
            joined = joined.replace('\u200b', '').replace('\xa0', ' ')
            lines = [line.strip() for line in joined.splitlines() if line.strip()]

            # Pattern variations: "#1 - Name - Series" or "1. Name — Series" or "1) Name - Series"
            patterns = [
                re.compile(r'^\#?\s*(\d{1,4})\s*[-.)]\s*(.*?)\s*[-–—]\s*(.+)$'),  # "#1 - Name - Series" or "1. Name — Series"
                re.compile(r'^\s*(\d{1,4})\.\s*(.*?)\s*[-–—]\s*(.+)$'),  # "1. Name — Series"
                re.compile(r'^\s*(\d{1,4})\s*-\s*(.*?)\s*-\s*(.+)$'),  # "1 - Name - Series"
            ]

            found = 0
            for line in lines:
                # Skip short lines unlikely to contain entries
                if len(line) < 6:
                    continue
                parsed = None
                for pat in patterns:
                    m = pat.match(line)
                    if m:
                        try:
                            rank = int(m.group(1))
                            name = m.group(2).strip()
                            series = m.group(3).strip()
                            parsed = (rank, name, series)
                            break
                        except Exception:
                            parsed = None
                if parsed:
                    rank, name, series = parsed
                    # sanitize common noise
                    name = re.sub(r'<:[^>]+>', '', name).strip()
                    series = re.sub(r'<:[^>]+>', '', series).strip()
                    entry = {
                        "rank": rank,
                        "name_display": name,
                        "series_display": series,
                        "list_type": self.current_list
                    }
                    self.collected_data.append(entry)
                    found += 1

            logger.info(f"Processed top embed page={page} found {found} entries (total collected={len(self.collected_data)})")

            # Optionally auto-save every N pages to avoid losing data
            # We'll save immediately for reliability
            if found > 0:
                saved = await self.save_collected_to_db()
                logger.info(f"Saved {saved} entries from page {page} to DB")

            return True

        except Exception as e:
            logger.error(f"Error processing top embed: {e}")
            return False

    async def save_collected_to_db(self) -> int:
        """
        Upsert all collected_data entries into DB.
        Returns count of processed entries.
        """
        count = 0
        # Use the crud.upsert_character which handles normalization & merge rules
        for entry in list(self.collected_data):  # copy to avoid mutation issues
            try:
                rank = entry.get("rank", 0)
                name = entry.get("name_display", "")
                series = entry.get("series_display", "")
                if self.current_list in ("claimed", "claim", "claimed_list"):
                    await upsert_character(name_display=name, series_display=series, claim_rank=rank, data_source="top_claimed")
                else:
                    await upsert_character(name_display=name, series_display=series, like_rank=rank, data_source="top_liked")
                count += 1
                # Optionally remove from collected_data after saving
                self.collected_data.remove(entry)
            except Exception as e:
                logger.error(f"Failed saving entry {entry}: {e}")
        return count

    async def complete_scraping(self):
        """Finish scraping run: save leftovers and mark complete."""
        if not self.scraping:
            return
        leftovers = await self.save_collected_to_db()
        self.scraping = False
        logger.info(f"Top list scraping complete. Leftovers saved: {leftovers}")

    def set_expected_manual_page(self, page: int):
        """Call this when owner types the helper command to indicate next $top page."""
        self.expected_manual_page = page
