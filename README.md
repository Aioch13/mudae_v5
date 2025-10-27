🧠 Mudae Helper Bot V3
Smart Auto-Assistant for Mudae Rolls and Series Ranking

The Mudae Helper Bot V3 is a Discord companion bot that watches your rolls, analyzes them using data from your local mudae.db, and sends private DM alerts for rare or valuable characters.
It combines AI-like ranking logic, series-level analysis, and customizable alert thresholds to enhance your Mudae gameplay experience.

✨ Key Features
🎲 Smart Roll Detection

Automatically monitors all Mudae roll and claim embeds in real-time.

Parses character information ($wa, $ha, $im, etc.) and updates your database automatically.

Works silently in the background — no command spam.

💎 Intelligent Recommender System

Evaluates each rolled character based on:

Meta Rank (popularity/claim rank)

Kakera Value

Series Popularity (from series.db)

Triggers a private DM alert when a high-value or top-tier character appears.

🔔 Personalized DM Alerts

Sends instant DMs with character name, meta rank, kakera, and image preview.

Tier badges (S, A, B, C, D) for visual clarity.

Fully configurable alert sensitivity via Discord commands.

🧮 Automated Series Ranking

series_rank.py builds a ranked database (series.db) using mudae.db data.

Series are graded from S → D Tier based on frequency and rank of top characters.

The recommender uses this data to decide when to ping or DM you.

🧾 Dynamic Configuration

Adjust all key thresholds directly in Discord without editing code:

Kakera threshold

Meta rank limit

DM sensitivity level

Series tracking limit

⚙️ Real-Time Commands

You can test, tune, and visualize how your settings behave with built-in commands.

⚡ Quick Start
1️⃣ Prerequisites

Python 3.10+

discord.py 2.x

aiosqlite, pandas, python-dotenv

Valid Discord Bot Token

mudae.db (scraped from Mudae rolls)

series.db (built with series_rank.py)

2️⃣ Setup

Create a .env file in the project root:

DISCORD_TOKEN=your_token_here
OWNER_ID=your_discord_id
KAKERA_THRESHOLD=100
META_RANK_THRESHOLD=5000
TOP_SERIES_LIMIT=50
TOP_SERIES_CACHE_TIME=1800

3️⃣ Run
python run.py


The bot will connect to your Discord and begin monitoring Mudae rolls.

🧩 How It Works
🧱 Core Components
Module	Purpose
recommender_listener_v2.py	Listens for Mudae embeds, parses rolls, and triggers DM logic.
src/bot/db/series_rank.py	Builds and updates series.db based on Mudae’s top characters.
src/bot/recommender/recommendator.py	Computes top series and global ranking info.
src/bot/parsers/im_parser.py	Parses $im embeds into structured character data.
src/bot/db/crud.py	Handles character insertions and updates.
🔍 Logic Overview

Owner rolls a character ($wa, $ha, etc.).

Bot captures Mudae’s response embed → parses the character info.

Character data is inserted/updated into mudae.db.

Recommender checks:

Is the character’s meta rank ≤ 5000?

Is kakera ≥ 100?

Is their series tier ≥ B (or within top series)?

If any of the above are true → the bot sends you a DM.

💬 Commands Overview
Command	Description
!testdm	Sends a test DM to verify that alerts are working.
!simulate_roll_debug <name>	Simulates how a real roll would be processed and shows whether it would trigger a DM.
!show_config	Displays your current DM thresholds and sensitivity.
!set_kakera <value>	Sets minimum Kakera value for alerts (e.g. !set_kakera 120).
!set_meta <value>	Sets maximum Meta Rank for alerts (lower = rarer).
!set_dm_sensitivity <1–5>	Adjusts DM strictness (1 = only rarest, 5 = frequent alerts).
!set_series_limit <value>	Defines how many top series are tracked by recommender.
!help_recommender	Shows full command reference and usage tips.
🧠 DM Trigger Logic (Simplified)
Condition	Description
meta_rank ≤ 5000	Character is among top 5,000 globally.
kakera_value ≥ 100	Character is valuable in kakera terms.
series_tier ∈ {S, A, B}	Character belongs to a highly ranked series.
claimed_roll == True	Automatically DMs if already claimed.

If any of the above are true → a DM alert is sent.
You can customize thresholds dynamically via Discord commands.

🪄 Tier System
Tier	Description	Example Trigger
S	Legendary / most popular series	“KonoSuba”, “Genshin Impact”
A	Highly popular	“One Piece”, “Demon Slayer”
B	Strong cult following	“Black Clover”, “Komi-san”
C	Mid-range	Niche anime or small franchises
D	Low or unranked	Obscure / uncommon series
📬 Example DM Output

💎 Megumin — S Tier
Series: Kono Subarashii Sekai ni Shukufuku
Meta Rank: 391
Kakera: 403
Top Series: ✅
Claimed: ❌

(with character image preview)

🧰 Developer Notes (for casual users)

The bot uses local SQLite databases (mudae.db, series.db) — no external servers.

Logs and debug prints appear in the terminal window.

Uses Discord embeds for cleaner DM formatting.

Sensitive tokens are hidden via .env file.

🏁 Summary

✅ Fully automated Mudae roll monitoring
✅ Smart rarity and series detection
✅ DM alerts for rare or high-tier characters
✅ Dynamic Discord configuration
✅ Simple setup — no coding required