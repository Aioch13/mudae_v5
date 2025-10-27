# src/bot/main.py
import sys
from pathlib import Path
import discord
from discord.ext import commands
from discord.ext import commands as _commands

# --- Ensure project root is importable ---
sys.path.append(str(Path(__file__).resolve().parents[2]))

# --- Project imports ---
from src.bot.config import DISCORD_TOKEN
from src.bot.utils.logger import setup_logger

# --- Setup logger and intents ---
logger = setup_logger()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# allow prefix $ and ! plus mention
bot = commands.Bot(command_prefix=_commands.when_mentioned_or("$", "!"), intents=intents)


@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    """Handles incoming Discord messages - passes to command processor."""
    # Let the RecommenderListenerV2 cog handle Mudae messages and $im commands
    await bot.process_commands(message)


# ------------------------------------------------------------
# ✅ Proper Cog setup for Recommender Listener
# ------------------------------------------------------------
@bot.event
async def setup_hook():
    """Load async extensions before the bot becomes ready."""
    # 🆕 FIXED: Correct import paths
    from src.bot.recommender.recommender_listener_v2 import RecommenderListenerV2
    await bot.add_cog(RecommenderListenerV2(bot))
    from src.bot.recommender.recommender_debug_cog import RecommenderDebugCog
    await bot.add_cog(RecommenderDebugCog(bot))
    logger.info("✅ Recommender listener + debug commands loaded.")


async def run_bot():
    """Start the bot safely."""
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing in environment variables.")
    await bot.start(DISCORD_TOKEN)