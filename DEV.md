🧩 Mudae Helper Bot V3 — Developer Handbook

Technical Reference and Maintenance Guide
Last updated: October 2025

🧠 Overview

Mudae Helper Bot V3 is a modular Discord companion that analyzes Mudae rolls and automates alerts.
It combines Discord event listeners, SQLite-based data storage, and ranking/recommendation logic into one self-contained ecosystem.

The bot operates in real time, parsing embeds, updating databases, ranking anime/game series, and triggering private DMs based on thresholds.

⚙️ System Architecture
🔧 Core Components
Module	Purpose
recommender_listener_v2.py	Main Discord event listener; parses Mudae messages and triggers recommendations & DMs.
src/bot/recommender/recommendator.py	Returns global/top series recommendations from series.db.
src/bot/db/series_rank.py	Builds and normalizes series.db rankings from mudae.db.
src/bot/db/crud.py	Handles database insertions and updates for character data.
src/bot/parsers/im_parser.py	Parses $im embeds into structured fields (name, series, kakera, etc).
src/bot/db/database.py	Async DB connection and utility functions.
data/mudae.db	Stores all parsed Mudae character data.
data/series.db	Stores computed series tier ranking data.

Recommended Structures

mudae-helper-bot-v3/
│
├── .env                         # Environment configuration (token, thresholds)
├── requirements.txt             # Python dependencies
├── run.py                       # Bot entrypoint
│
├── data/
│   ├── mudae.db                 # Main database (characters, meta data)
│   ├── series.db                # Generated from mudae.db by series_rank.py
│   └── backups/                 # Optional periodic backups
│
├── src/
│   └── bot/
│       ├── __init__.py
│       │
│       ├── recommender/
│       │   ├── recommendator.py       # Series recommendation logic
│       │   └── recommender_listener_v2.py  # Main Discord listener & DM logic
│       │
│       ├── db/
│       │   ├── database.py            # Async DB connection management
│       │   ├── crud.py                # Insert/update helpers for mudae.db
│       │   ├── series_rank.py         # Series scoring and tier generation
│       │   └── rebuild_meta_view.py   # Rebuilds characters_meta view
│       │
│       ├── parsers/
│       │   └── im_parser.py           # Extracts structured info from $im embeds
│       │
│       ├── utils/
│       │   └── logger_setup.py        # Optional: shared logging configuration
│       │
│       └── main.py                    # (if applicable) bot setup & cog loading
│
├── docs/
│   ├── README.md                      # User-facing setup & command guide
│   └── DEVELOPER_HANDBOOK.md          # This document
│
└── logs/
    └── bot.log                        # Optional runtime logs

🧩 Process Flow Diagram
┌──────────────────────────────┐
│  Discord Message Event       │
│  (Mudae roll or claim)       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ RecommenderListenerV2        │
│ Parses embeds + checks type  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ im_parser.py                 │
│ Extracts structured data     │
│ name, series, kakera, ranks  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ crud.py / mudae.db           │
│ Upserts character record     │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ series_rank.py / series.db   │
│ Computes avg_meta_rank, tiers│
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Recommender Decision Logic   │
│   if meta/kakera/tier OK → DM│
└──────────────────────────────┘

🧮 Database Schemas
📘 mudae.db

Contains all character data captured from Mudae embeds.

Column	Type	Description
id	INTEGER PRIMARY KEY	Auto increment key
name_display	TEXT	Character name
series_display	TEXT	Anime/Game source
claim_rank	INTEGER	Rank based on claim popularity
like_rank	INTEGER	Rank based on likes
kakera_value	INTEGER	Kakera value from Mudae
meta_rank	REAL	Average of claim & like ranks
updated_at	TIMESTAMP	Last update

The characters_meta view (rebuilt via rebuild_meta_view.py) simplifies queries by normalizing missing columns.

📗 series.db

Computed output from series_rank.py.

Column	Type	Description
series	TEXT	Series name
avg_meta_rank	REAL	Average rank of top characters
characters_in_top	INTEGER	How many top characters appear in this series
series_score	REAL	Weighted score combining frequency & rank
tier_score	REAL	Normalized 0–100 range
tier	TEXT	Tier classification (S, A, B, C, D)

Tiering logic:

if score >= 85: "S"
elif score >= 70: "A"
elif score >= 55: "B"
elif score >= 40: "C"
else: "D"

🔔 Recommender & DM Logic
🧠 Core Algorithm (RecommenderListenerV2.on_message)

Detects a Mudae message via name and embed presence.

Parses the embed → extracts structured data (parse_im_embed).

Saves/updates the character in mudae.db.

Looks up the character’s series tier from series.db.

Evaluates conditions:

should_dm = (
    (meta_rank and meta_rank <= META_RANK_THRESHOLD)
    or (kakera_value and kakera_value >= KAKERA_THRESHOLD)
    or (series_tier in {"S", "A", "B"})
)


Sends a rich embed DM with rarity color and emoji:

💎 S-tier → gold

🌟 A-tier → purple

⭐ B-tier → blue

✨ C-tier → teal

💤 D-tier → dark gray

⚙️ Threshold Configuration (Runtime)

The bot supports real-time adjustment via Discord commands — no restarts required.

Variable	Default	Command
KAKERA_THRESHOLD	100	!set_kakera <value>
META_RANK_THRESHOLD	5000	!set_meta <value>
TOP_SERIES_LIMIT	50	!set_series_limit <value>

Values are cached in memory for the current session.

🧰 Development Setup
1️⃣ Clone & Install
git clone https://github.com/your-repo/mudae-v3.git
cd mudae-v3
pip install -r requirements.txt

2️⃣ Environment

Create .env:

DISCORD_TOKEN=your_token_here
OWNER_ID=your_discord_id
KAKERA_THRESHOLD=100
META_RANK_THRESHOLD=5000

3️⃣ Generate Databases

If you have Mudae data:

python src/bot/db/rebuild_meta_view.py
python src/bot/db/series_rank.py

🧑‍💻 Debugging & Testing
🔍 Manual DM Test

Use inside Discord:

!testdm


→ Forces a sample DM to verify bot connection & permissions.

🧪 Simulation Debug
!simulate_roll_debug Megumin


→ Loads real DB data for that character and shows whether a DM would be triggered.

🧾 Logging

Logs print to terminal (or bot.log if configured):

[🎯] → Roll detected

[💌] → DM sent

[💤] → Ignored roll with reason

[⚠️] → DB or parsing error

🧱 Code Entry Points
File	Entry Role
run.py	Initializes bot, loads cogs, starts Discord client
recommender_listener_v2.py	Registered as Cog; contains all event listeners
series_rank.py	One-time or scheduled computation of series.db
recommendator.py	Provides ranked series data for the listener
crud.py	CRUD access layer for mudae.db
im_parser.py	Extracts data fields from embeds (supports $im, $wa, etc.)
🧩 Extension Guidelines

Adding a new ranking metric:
Extend series_rank.py → include new weighted factor in series_score.

Custom DM conditions:
Modify the should_dm section in recommender_listener_v2.py.

Extra Discord commands:
Add new @commands.command() in the listener class.
Remember to register them in your main bot.load_extension().

Database migrations:
Add helper SQL scripts in /src/bot/db/migrations/.
Use ALTER TABLE carefully; SQLite doesn’t support drop columns easily.

🧠 Troubleshooting
Symptom	Possible Cause	Fix
no such column: source	Outdated meta view	Run rebuild_meta_view.py
All series show Tier D	Scoring normalization failed or empty top-1000 sample	Ensure mudae.db has valid claim/like ranks
Bot silent on rolls	Bot not detecting Mudae messages	Check message.author name (“mudae”) or embed parsing
DM not sent	OWNER_ID invalid or Discord DMs disabled	Check .env values
DB locked	SQLite concurrent write	Add async locks or wait retries
🧭 Maintenance Tips

Schedule regular re-generation of series.db (weekly or monthly).

Back up mudae.db frequently; it holds all accumulated character data.

Encourage end users to use !show_config to verify their active settings.

Use simulate_roll_debug to regression-test after code changes.

Always run series_rank.py after schema modifications.

📘 Appendix: Tier Distribution Formula
series_score = (1 / avg_meta_rank) * 1e5 + (characters_in_top * 10)
tier_score = 100 * (series_score - min_score) / (max_score - min_score)


Tiers:

S: ≥ 85

A: 70–84

B: 55–69

C: 40–54

D: < 40

✅ Handoff Summary

Listener: recommender_listener_v2.py

Databases: mudae.db, series.db

Core trigger logic: meta_rank / kakera / series_tier

Fully configurable via Discord commands

Self-contained — no cloud dependencies

Ready for extension (v4-ready architecture)