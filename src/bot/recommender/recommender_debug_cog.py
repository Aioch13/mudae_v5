# src/bot/recommender/recommender_debug_cog.py
import os
import traceback
import logging
from typing import Optional, Dict, List

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Recommender helpers
from src.bot.recommender.recommendator import recommend_popular_series, recommend_top_characters
from src.bot.db.series_rank import tier_flavor_label, get_series_info

load_dotenv()
logger = logging.getLogger("mudae-helper.debug")
logger.setLevel(logging.INFO)

# ============================================================
# 👑 Unified Owner Handling (reads from config.py)
# ============================================================
from src.bot.config import OWNER_IDS, OWNER_ID

print(f"[👑] Active owner IDs: {', '.join(str(x) for x in OWNER_IDS)}")



async def _send_dm_to_owner(bot: commands.Bot, owner_id: int, embed: discord.Embed, log: logging.Logger):
    """Local helper to send a DM to an owner and return (ok: bool, err: Optional[str])."""
    try:
        # ensure int
        if isinstance(owner_id, str) and owner_id.isdigit():
            owner_id = int(owner_id)
        user = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
        if not user:
            log.error("debug_cog: owner not found for id=%s", owner_id)
            return False, "owner_not_found"
        await user.send(embed=embed)
        log.info("debug_cog: DM sent to owner %s (%s)", getattr(user, "name", None), owner_id)
        return True, None
    except discord.Forbidden as e:
        log.error("debug_cog: Forbidden sending DM to %s — %s", owner_id, e)
        return False, "forbidden"
    except discord.HTTPException as e:
        log.error("debug_cog: HTTPException sending DM to %s — %s", owner_id, e)
        return False, "http_exception"
    except Exception as e:
        log.error("debug_cog: Unexpected DM error for %s — %s\n%s", owner_id, e, traceback.format_exc())
        return False, "other"


class RecommenderDebugCog(commands.Cog):
    """Debug utilities aligned with the new DM logic and thresholds."""

    def __init__(self, bot):
        self.bot = bot
        self.owner_only_dm = os.getenv("OWNER_ONLY_DM", "true").lower() == "true"
        self.meta_rank_threshold = int(os.getenv("META_RANK_THRESHOLD", 5000))
        self.kakera_threshold = int(os.getenv("KAKERA_THRESHOLD", 100))
        self.top_series_limit = int(os.getenv("TOP_SERIES_LIMIT", 50))
        self.logger = logger
        print(f"[⚙️] DebugCog loaded | Owner-only={self.owner_only_dm}, Meta≤{self.meta_rank_threshold}, Kakera≥{self.kakera_threshold}")

    # ------------------------------------------------------------
    # Manual DM test — simulate a real DM
    # ------------------------------------------------------------
    @commands.command(name="testdm_debug")
    async def testdm_debug(self, ctx, *, name: str = "Zero Two"):
        """Simulate the DM decision logic for a single character and optionally send a DM to owner."""
        # permission guard
        if self.owner_only_dm and ctx.author.id not in OWNER_IDS:
            await ctx.send("🚫 Owner-only DM mode is ON — only owner can run this test.")
            return

        # Simulated parsed roll data
        parsed = {
            "name_display": name,
            "series_display": "Darling in the Franxx",
            "kakera_value": 250,
            "claim_rank": 100,
            "like_rank": 120,
            "image_url": "https://mudae.net/uploads/12345/sample.png",
        }

        # compute meta
        meta_rank = (parsed["claim_rank"] + parsed["like_rank"]) // 2 if parsed.get("claim_rank") and parsed.get("like_rank") else None

        # determine series tier by checking series DB or popular list
        series_tier = None
        try:
            si = get_series_info(parsed["series_display"])
            series_tier = si["tier"] if si else None
        except Exception:
            series_tier = None

        # fallback: check popular series if no series_info
        if not series_tier:
            try:
                popular = await recommend_popular_series(limit=self.top_series_limit)
                for s in popular:
                    if s.get("series", "").lower() == parsed["series_display"].lower():
                        series_tier = s.get("tier")
                        break
            except Exception:
                pass

        # friendly tier/flavor
        tier_label = series_tier or "Unknown"
        tier_flavor = tier_flavor_label(series_tier) if series_tier else "❔ Unknown Tier"

        # decision (meta-first, then series-popularity)
        will_alert = False
        reasons = []
        if meta_rank is not None and meta_rank <= self.meta_rank_threshold:
            will_alert = True
            reasons.append(f"Meta≤{self.meta_rank_threshold} ({meta_rank})")
        elif series_tier and series_tier.upper() in ("S", "A"):
            will_alert = True
            reasons.append(f"Series-tier {series_tier}")
        elif parsed.get("kakera_value") and parsed["kakera_value"] >= self.kakera_threshold:
            will_alert = True
            reasons.append(f"Kakera≥{self.kakera_threshold} ({parsed['kakera_value']})")

        # build embed
        color = discord.Color.gold() if will_alert else discord.Color.dark_grey()
        embed = discord.Embed(
            title=f"🎯 {parsed['name_display']} — {tier_label}",
            description=(
                f"**Series:** {parsed['series_display']}\n"
                f"**Tier:** {tier_label}\n"
                f"**Meta Rank:** {meta_rank or '❔'}\n"
                f"**Kakera:** {parsed.get('kakera_value') or '❔'}\n"
                f"**Decision:** {'✅ DM Sent' if will_alert else '💤 No DM'}\n"
                f"**Reasons:** {', '.join(reasons) if reasons else 'None'}"
            ),
            color=color,
        )
        if parsed.get("image_url"):
            embed.set_thumbnail(url=parsed["image_url"])

        # send DM to owner if will_alert; else just show
        if will_alert:
            ok, err = await _send_dm_to_owner(self.bot, OWNER_ID, embed, self.logger)
            if ok:
                await ctx.send(f"✅ Sent test DM to owner for **{parsed['name_display']}**.")
            else:
                await ctx.send(f"⚠️ Failed to send DM: {err}")
        else:
            await ctx.send(embed=embed)

    # ------------------------------------------------------------
    # Simulate full roll evaluation using actual DB data
    # ------------------------------------------------------------
    @commands.command(name="simulate_debug_roll")
    async def simulate_debug_roll(self, ctx, *, name: str):
        """Simulate a recommender evaluation using actual DB data for a given character."""
        from src.bot.db.database import get_conn

        # permission guard
        if self.owner_only_dm and ctx.author.id not in OWNER_IDS:
            await ctx.send("🚫 Owner-only DM mode is ON — only owner can run this simulation.")
            return

        async with ctx.typing():
            conn = await get_conn()
            cursor = await conn.execute("""
                SELECT name_display, series_display, kakera_value, claim_rank, like_rank, meta_rank
                FROM characters_meta
                WHERE LOWER(name_display) = LOWER(?)
                LIMIT 1
            """, (name,))
            row = await cursor.fetchone()
            await conn.close()

            if not row:
                await ctx.send(f"❌ No character found for **{name}** in your DB.")
                return

            parsed = {
                "name_display": row[0],
                "series_display": row[1],
                "kakera_value": row[2],
                "claim_rank": row[3],
                "like_rank": row[4],
                "meta_rank": row[5],
            }

            kakera_value = parsed["kakera_value"]
            meta_rank = parsed["meta_rank"] or (
                (parsed["claim_rank"] + parsed["like_rank"]) // 2
                if parsed["claim_rank"] and parsed["like_rank"]
                else None
            )

            # --- get series tier
            try:
                series_info = get_series_info(parsed["series_display"])
                series_tier = series_info["tier"] if series_info else "Unknown"
            except Exception:
                series_tier = "Unknown"

            # --- get popularity info
            try:
                popular_series = await recommend_popular_series(limit=self.top_series_limit)
                popular_match = any(
                    s["series"].lower() == parsed["series_display"].lower()
                    for s in popular_series
                )
            except Exception:
                popular_match = False

            # --- DM trigger logic (same as production)
            meta_ok = meta_rank is not None and meta_rank <= self.meta_rank_threshold
            kakera_ok = kakera_value is not None and kakera_value >= self.kakera_threshold
            tier_ok = series_tier and series_tier.upper() in ("S", "A")
            should_dm = meta_ok or kakera_ok or tier_ok

            # --- build result embed
            color = discord.Color.green() if should_dm else discord.Color.dark_grey()
            emoji = "💌" if should_dm else "💤"
            desc = (
                f"**Series:** {parsed['series_display']}\n"
                f"**Series Tier:** {series_tier}\n"
                f"**Meta Rank:** {meta_rank or '❔'}\n"
                f"**Kakera:** {kakera_value or '❔'}\n"
                f"**Popular Series:** {'✅' if popular_match else '❌'}\n\n"
                f"**Meta Check:** {'✅' if meta_ok else '❌'}\n"
                f"**Tier Check:** {'✅' if tier_ok else '❌'}\n"
                f"**Kakera Check:** {'✅' if kakera_ok else '❌'}"
            )
            embed = discord.Embed(
                title=f"{emoji} Simulation — {parsed['name_display']}",
                description=desc,
                color=color,
            )
            await ctx.send(embed=embed)
            if should_dm:
                await ctx.send("✅ This roll **would trigger** a DM under live conditions.")
            else:
                await ctx.send("💤 This roll **would NOT** trigger a DM.")
    # ============================================================
    # 📊 Check Series Ranking / Tier
    # ============================================================
    @commands.command(name="series_rank")
    async def series_rank(self, ctx, *, series_name: str):
        """Check the tier and ranking info of a specific anime/game series."""
        try:
            from src.bot.db.series_rank import get_series_info
            info = get_series_info(series_name)
            if not info:
                await ctx.send(f"❌ No ranking data found for **{series_name}**.")
                return

            tier = info.get("tier", "Unknown")
            rank = info.get("rank", "?")
            popularity = info.get("popularity", "N/A")

            color_map = {
                "S": discord.Color.gold(),
                "A": discord.Color.purple(),
                "B": discord.Color.blue(),
                "C": discord.Color.teal(),
                "D": discord.Color.dark_grey(),
            }
            color = color_map.get(tier, discord.Color.blurple())

            embed = discord.Embed(
                title=f"🏆 Series Ranking — {series_name}",
                description=(
                    f"**Tier:** {tier}\n"
                    f"**Global Rank:** {rank}\n"
                    f"**Popularity Score:** {popularity}\n"
                ),
                color=color,
            )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⚠️ Failed to fetch series info: {e}")



    # ------------------------------------------------------------
    # Toggle Owner-only mode
    # ------------------------------------------------------------
    @commands.command(name="toggle_owner_only_debug")
    async def toggle_owner_only_debug(self, ctx):
        self.owner_only_dm = not self.owner_only_dm
        mode = "ON (owner only)" if self.owner_only_dm else "OFF (all users)"
        await ctx.send(f"✅ Owner-only DM mode toggled: **{mode}**")
        print(f"[⚙️] Debug owner-only mode now {mode}")


async def setup(bot):
    await bot.add_cog(RecommenderDebugCog(bot))
