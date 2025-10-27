import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "data/mudae.db")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# ============================================================
# 👑 Owner ID Handling — supports multiple or single IDs
# ============================================================

# Read from OWNER_IDS first, then fall back to OWNER_ID
owner_env = os.getenv("OWNER_IDS") or os.getenv("OWNER_ID", "")

OWNER_IDS = [
    int(x.strip())
    for x in owner_env.split(",")
    if x.strip().isdigit()
]

if not OWNER_IDS:
    OWNER_IDS = [0]

# Keep backward compatibility for modules expecting OWNER_ID
OWNER_ID = OWNER_IDS[0]

# Optional startup printout
if len(OWNER_IDS) > 1:
    print(f"[👑] Multiple owners detected: {', '.join(str(x) for x in OWNER_IDS)}")
else:
    print(f"[👑] Single owner: {OWNER_ID}")
