# ============================================================
# 🧠 Mudae Recommender Listener — Cleaned & Optimized Version
# ============================================================

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from src.bot.config import OWNER_IDS
from src.bot.parsers.im_parser import parse_im_embed
from src.bot.db.crud import upsert_character_from_im, get_character_info
from src.bot.recommender.recommendator import recommend as recommend_global
from src.bot.db.series_rank import get_series_info
from src.bot.utils.env_config import write_env

# ============================================================
# 🔧 Environment & Globals
# ============================================================

load_dotenv()

OWNER_IDS_ENV = os.getenv("OWNER_IDS", "")
# ============================================================
# 👑 Unified Owner Handling (reads from config.py)
# ============================================================
from src.bot.config import OWNER_IDS, OWNER_ID

print(f"[👑] Active owner IDs: {', '.join(str(x) for x in OWNER_IDS)}")


# ============================================================
# 🎯 Main Listener Class
# ============================================================

class RecommenderListenerV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        import logging
        self.logger = logging.getLogger("mudae-helper.recommender")

        # Core thresholds
        self.kakera_threshold = int(os.getenv("KAKERA_THRESHOLD", 100))
        self.meta_rank_threshold = int(os.getenv("META_RANK_THRESHOLD", 5000))
        self.top_series_limit = int(os.getenv("TOP_SERIES_LIMIT", 50))
        self.top_series_cache_time = int(os.getenv("TOP_SERIES_CACHE_TIME", 1800))
        self.dm_tier_threshold = os.getenv("DM_TIER_THRESHOLD", "B").upper()
        self.owner_only_dm = os.getenv("OWNER_ONLY_DM", "true").lower() == "true"

        # State tracking
        self.last_roller_name = None
        self._last_owner_roll = None

        # Startup log
        print(f"[⚙️] Owner-only DM mode: {self.owner_only_dm}")
        print("[✅] Recommender listener loaded.")
        print(f"[⚙️] Kakera threshold: {self.kakera_threshold}")
        print(f"[⚙️] Meta rank threshold: {self.meta_rank_threshold}")
        print(f"[⚙️] DM Tier Threshold: {self.dm_tier_threshold}+")
        print(f"[⚙️] Top-series limit: {self.top_series_limit} (cache {self.top_series_cache_time}s)")

    # ============================================================
    # 📩 Main on_message Listener
    # ============================================================
# ============================================================
# 🔧 PATCH: Fixed Owner Detection & Tier Logic (NO DB UPSERT FOR ROLLS)
# ============================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles Mudae rolls, embeds, and DM alerts."""
    

        # --- 1️⃣ Track Owner Roll
        try:
            author_id = message.author.id
        except Exception:
            return

        content_lower = (message.content or "").lower()
        # 🆕 FIX: Check all OWNER_IDS, not just OWNER_ID
        if author_id in OWNER_IDS and any(cmd in content_lower for cmd in ["$wa", "$wg", "$ha", "$hg", "$ma", "$mg","$mx", "$waifu"]):
            self.last_roller_name = (message.author.display_name or message.author.name or "").lower()
            self._last_owner_roll = self.last_roller_name
            print(f"[🎲] Owner rolled: {message.content} — awaiting embed for '{self.last_roller_name}'")
            return

        # --- 2️⃣ Filter: only Mudae embeds
        if not message.author or "mudae" not in (message.author.name or "").lower() or not message.embeds:
            return

        embed = message.embeds[0]
        desc_lower = (embed.description or "").lower()
        footer_lower = (embed.footer.text or "").lower() if embed.footer else ""

        # --- 3️⃣ Skip Mudae utility embeds
        ignored = ["$top", "$mm", "$tu", "$help", "$info", "$note", "$bonus", "$dk", "$rt"]
        if any(content_lower.startswith(cmd) for cmd in ignored):
            print(f"[🚫] Ignored utility message ({content_lower})")
            return

        # --- 4️⃣ Handle $im updates - SIMPLE DATA-DRIVEN APPROACH
        parsed = parse_im_embed(embed)
        
        # 🆕 SIMPLE LOGIC: If we have any non-NULL rank data, it's an $im response
        has_valid_data = (
            parsed and 
            any(value is not None for value in [
                parsed.get('kakera_value'), 
                parsed.get('claim_rank'), 
                parsed.get('like_rank')
            ])
        )

        if has_valid_data:
            print(f"[ℹ️] Processing $im response (has valid data)")

            # 🧩 Normalize field names to match DB schema
            normalized = {
                "name_display": parsed.get("name_display") or parsed.get("name"),
                "series_display": parsed.get("series_display") or parsed.get("series"),
                "kakera_value": parsed.get("kakera_value"),
                "claim_rank": parsed.get("claim_rank"),
                "like_rank": parsed.get("like_rank"),
            }

            # 🧩 Drop any None keys before DB call (prevents null overwrites)
            clean_data = {k: v for k, v in normalized.items() if v is not None}

            try:
                result = await upsert_character_from_im(**clean_data)

                kakera = clean_data.get('kakera_value', 'None')
                claim = clean_data.get('claim_rank', 'None')
                like = clean_data.get('like_rank', 'None')

                if result == "new":
                    print(f"[🆕] NEW ENTRY from $im: {clean_data.get('name_display')} | {clean_data.get('series_display')} (Kakera={kakera}, Claim={claim}, Like={like})")
                else:
                    print(f"[🔁] Updated from $im: {clean_data.get('name_display')} | {clean_data.get('series_display')} (Kakera={kakera}, Claim={claim}, Like={like})")

            except Exception as e:
                print(f"[⚠️] DB upsert error: {e}")

            print("[🚫] Skipping DM logic for $im — info-only update.")
            return


        # ============================================================
        # 5️⃣ Detect Roll / Claim
        # ============================================================
        # Only reaches here if it's NOT an $im response (no valid data)
        claimed_roll = any(p in desc_lower or p in footer_lower for p in ["belongs to", "is married to", "claimed by"])
        new_roll = any(p in desc_lower for p in ["react with any emoji to claim", "react with any emoji to claim!"])
        user_roll = self.last_roller_name and (
            self.last_roller_name in desc_lower or self.last_roller_name in footer_lower
        )

        if not (claimed_roll or new_roll or user_roll):
            print("[🚫] Ignored embed: not a roll/claim pattern.")
            return

        print("🎯 Detected roll embed — parsing...")
        parsed = parse_im_embed(embed) or {}
        name_display = parsed.get("name_display") or parsed.get("name") or "Unknown"
        series_display = parsed.get("series_display") or parsed.get("series") or "Unknown"
        print(f"[📦] Parsed: {name_display} | {series_display}")

        # 🆕 CRITICAL: Prevent roll data from being mistaken for $im
        # Rolls should NEVER write to database - only read from it
        print(f"[🛡️] Roll protection: Ensuring no DB write for roll data")
        # Explicitly skip any database upsert for rolls

        # ============================================================
        # 6️⃣ Fetch DB Info
        # ============================================================
        db_info = await get_character_info(name_display, series_display)
        if db_info:
            print(f"[🧠] DB entry found: Kakera={db_info.get('kakera_value')} Claim={db_info.get('claim_rank')} Like={db_info.get('like_rank')}")
        else:
            print(f"[🕳️] No DB record for {name_display} | {series_display}")

        # Merge parsed + DB
        payload = {
            "name_display": name_display,
            "series_display": series_display,
            "kakera_value": parsed.get("kakera_value") or (db_info or {}).get("kakera_value"),
            "claim_rank": parsed.get("claim_rank") or (db_info or {}).get("claim_rank"),
            "like_rank": parsed.get("like_rank") or (db_info or {}).get("like_rank"),
        }

        print("\n" + "═" * 65)
        emoji_type = "🫶" if claimed_roll else "🎲"
        print(f"{emoji_type} **Processing Roll:** {name_display} | {series_display}")
        print(f"💎 Kakera: {payload['kakera_value'] or '❔'} | 📈 Claim Rank: {payload['claim_rank'] or '❔'} | 💖 Like Rank: {payload['like_rank'] or '❔'}")
        print("──────────────────────────────")

        # ============================================================
        # 7️⃣ Compute Meta / Rank Logic
        # ============================================================
        kakera_value = payload["kakera_value"]
        claim_rank = payload["claim_rank"]
        like_rank = payload["like_rank"]

        try:
            kakera_value = int(kakera_value) if kakera_value else None
        except (ValueError, TypeError) as e:
            print(f"[⚠️] Kakera conversion failed: {e}")
            kakera_value = None
            
        try:
            claim_rank = int(claim_rank) if claim_rank else None
        except (ValueError, TypeError) as e:
            print(f"[⚠️] Claim rank conversion failed: {e}")
            claim_rank = None
            
        try:
            like_rank = int(like_rank) if like_rank else None
        except (ValueError, TypeError) as e:
            print(f"[⚠️] Like rank conversion failed: {e}")
            like_rank = None

        meta_rank = None
        if claim_rank and like_rank:
            meta_rank = (claim_rank + like_rank) // 2
        elif claim_rank:
            meta_rank = claim_rank
        elif like_rank:
            meta_rank = like_rank

        payload.update({
            "kakera_value": kakera_value,
            "claim_rank": claim_rank,
            "like_rank": like_rank,
            "meta_rank": meta_rank,
        })

        print(f"💭 Evaluating: Meta ≤ {self.meta_rank_threshold}, Kakera ≥ {self.kakera_threshold}, Tier ≥ {self.dm_tier_threshold}")
        print(f"🧮 Computed Meta Rank: {meta_rank or '❔'}")

        # ============================================================
        # 8️⃣ DM Decision Logic (Priority-based + Detailed Debug Output)
        # ============================================================
        should_dm = False
        reasons = []
        series_name = series_display or "Unknown"
        series_tier = "Unknown"

        # 🏆 1️⃣ Claimed rolls ALWAYS trigger a DM
        claimed_keywords = ["belongs to", "is married to", "claimed by", "has claimed", "💍"]
        claimed_roll = any(
            kw in desc_lower or kw in footer_lower or kw in (embed.title or "").lower()
            for kw in claimed_keywords
        )

        # 🩵 Detect purple "claimed" embed color (Mudae uses ~0xf47fff)
        if hasattr(embed, "color") and embed.color:
            color_val = embed.color.value
            if 0xf47ff0 <= color_val <= 0xf480ff:
                claimed_roll = True

        if claimed_roll:
            should_dm = True
            print("[🏆] Claimed roll detected — DM will be sent unconditionally.")

        # 💎 2️⃣ Hard block: if Kakera known and below threshold (and not claimed)
        kakera_known = kakera_value is not None
        kakera_low = kakera_known and kakera_value < self.kakera_threshold
        if kakera_low and not claimed_roll:
            reasons.append(f"💎 Kakera too low ({kakera_value} < {self.kakera_threshold})")
            should_dm = False
        else:
            # 🧮 3️⃣ Continue with Meta / Series logic
            meta_ok = meta_rank and meta_rank <= self.meta_rank_threshold
            kakera_ok = kakera_value and kakera_value >= self.kakera_threshold

            try:
                series_info = get_series_info(series_name)
                series_tier = series_info["tier"] if series_info else "Unknown"
            except Exception as e:
                print(f"[⚠️] Series info fetch failed: {e}")
                series_tier = "Unknown"

            tier_val = {"S":5,"A":4,"B":3,"C":2,"D":1,"Unknown":0}
            required_tier_val = tier_val.get(self.dm_tier_threshold, 3)
            current_tier_val = tier_val.get(series_tier, 0)
            tier_ok = current_tier_val >= required_tier_val

            if not should_dm:
                if meta_ok:
                    should_dm = True
                elif tier_ok:
                    should_dm = True
                elif kakera_ok:
                    should_dm = True

            # Collect reasons for debugging
            if not meta_ok:
                reasons.append(f"📉 Meta too high ({meta_rank or '❔'} > {self.meta_rank_threshold})")
            if not tier_ok:
                reasons.append(f"🏷️ Tier below {self.dm_tier_threshold} ({series_tier or 'Unknown'})")
            if not kakera_ok:
                reasons.append(f"💎 Kakera below {self.kakera_threshold} ({kakera_value or '❔'})")

        # ✅ 4️⃣ Claimed rolls override everything
        if claimed_roll:
            should_dm = True
            reasons.clear()  # claimed rolls ignore all failure reasons

        # ✅ Unified single output block (with bright blue highlight)
        if should_dm:
            BLUE_BOLD = "\033[1;94m"
            RESET = "\033[0m"

            print(
                f"{BLUE_BOLD}💌 **DM Triggered!**{RESET}\n"
                f"   • 🎯 Claimed: {'✅' if claimed_roll else '❌'}\n"
                f"   • 💎 Kakera: {kakera_value or '❔'} (≥ {self.kakera_threshold})\n"
                f"   • 📈 Meta Rank: {meta_rank or '❔'} (≤ {self.meta_rank_threshold})\n"
                f"   • 🏆 Series Tier: {series_tier or 'Unknown'} (≥ {self.dm_tier_threshold})\n"
                f"{BLUE_BOLD}{'═' * 60}{RESET}"
            )
        else:
            print("💤 **No DM Sent.** Reasons:")
            for r in reasons:
                print(f"   • {r}")
            print("──────────────────────────────")


        payload.update({"should_dm": should_dm, "series_tier": series_tier})


        # ============================================================
        # 🆕 FIXED: Owner-only Mode Check
        # ============================================================
        if self.owner_only_dm:
            # Check if this is an owner roll by name matching
            is_owner_roll = (
                self._last_owner_roll and 
                self._last_owner_roll in (desc_lower + footer_lower)
            )
            if not is_owner_roll:
                print("[🚫] Ignored DM: Non-owner roll (owner-only mode).")
                return

        if not should_dm:
            print("💭 Decision: No DM triggered.")
            return

        # ============================================================
        # 🔟 Send DM Embed
        # ============================================================
        owner_ids = OWNER_IDS or [OWNER_ID]
        emoji_map = {"S":"💎","A":"🌟","B":"⭐","C":"✨","D":"💤","Unknown":"🎯"}
        color_map = {"S":discord.Color.gold(),"A":discord.Color.purple(),"B":discord.Color.blue(),
                     "C":discord.Color.teal(),"D":discord.Color.dark_grey(),"Unknown":discord.Color.dark_grey()}
        emoji = emoji_map.get(series_tier,"🎯")
        color = color_map.get(series_tier,discord.Color.dark_grey())

        dm_embed = discord.Embed(
            title=f"{emoji} {name_display} — {series_tier}-Tier",
            description=(
                f"**Series:** {series_display}\n"
                f"**Meta Rank:** {meta_rank or '❔'}\n"
                f"**Kakera:** {kakera_value or '❔'}\n"
                f"**Claimed:** {'✅' if claimed_roll else '❌'}"
            ),
            color=color
        )

        # 🆕 IMPROVED: Safe image handling
        if hasattr(embed, 'image') and embed.image and hasattr(embed.image, 'url') and embed.image.url:
            dm_embed.set_image(url=embed.image.url)
        elif hasattr(embed, 'thumbnail') and embed.thumbnail and hasattr(embed.thumbnail, 'url') and embed.thumbnail.url:
            dm_embed.set_thumbnail(url=embed.thumbnail.url)

        for oid in owner_ids:
            try:
                user = await self.bot.fetch_user(int(oid))
                if user:
                    await user.send(embed=dm_embed)
                    print(f"[💌] DM sent to {user.name} for {name_display} | Tier={series_tier}")
            except Exception as e:
                print(f"[❌] DM failed for {oid}: {e}")

        # 🆕 CLEANUP: Reset roll tracking
        self._last_owner_roll = None
        self.last_roller_name = None

        print("🏁 Roll processing complete - exiting")

        # 🆕 ADD THIS RETURN STATEMENT:
        return
        # This prevents the code from continuing to the $im detection logic