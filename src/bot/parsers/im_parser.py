# src/bot/parsers/im_parser.py
import re
import logging

logger = logging.getLogger("mudae-helper.parser.im")

# Toggle when you want to see full embed dicts for debugging
DEBUG_RAW_EMBED = False


def _clean_emoji_and_tags(s: str) -> str:
    """Remove Discord emoji tags and kakera/gender symbols, preserving punctuation."""
    return re.sub(r'<:[^>]+>|[💎♦♂♀]', '', (s or "")).strip()


def _parse_int_with_commas(s: str):
    """Convert strings like '6,000' or '1000' to int, return None if invalid."""
    if not s:
        return None
    try:
        return int(str(s).replace(",", "").strip())
    except ValueError:
        return None


def parse_im_embed(embed):
    """
    Robust parser for Mudae $im embeds.
    Returns dict: {name, series, kakera_value, claim_rank, like_rank}
    """

    # Optional debug of raw embed structure
    try:
        if DEBUG_RAW_EMBED and hasattr(embed, "to_dict"):
            logger.debug("RAW EMBED DICT: %s", embed.to_dict())
    except Exception:
        logger.exception("Failed to log raw embed")

    char_name = ""
    series = ""
    kakera_value = None
    claim_rank = None
    like_rank = None

    # --- Early guard: reject non-character embeds ---
    title_text = getattr(embed, "title", "") or ""
    author_text = getattr(embed.author, "name", "") if getattr(embed, "author", None) else ""
    title_low = title_text.lower().strip()
    author_low = author_text.lower().strip()

    if any(k in title_low for k in ["top", "roulette", "daily", "ranking", "claim rank", "like rank"]):
        logger.debug(f"Rejected non-character embed by title: {title_text}")
        return {"name": None, "series": None, "kakera_value": None, "claim_rank": None, "like_rank": None}
    if any(k in author_low for k in ["top", "roulette", "daily", "ranking"]):
        logger.debug(f"Rejected non-character embed by author: {author_text}")
        return {"name": None, "series": None, "kakera_value": None, "claim_rank": None, "like_rank": None}

    # --- Character name ---
    if author_text:
        char_name = _clean_emoji_and_tags(author_text)
    elif title_text:
        char_name = _clean_emoji_and_tags(title_text)

    # --- Description analysis ---
    desc = embed.description or ""
    lines = [l.strip() for l in desc.splitlines() if l.strip()]

    if lines:
        first_line = _clean_emoji_and_tags(lines[0])
        if (
            first_line
            and len(first_line) > 2
            and not any(k in first_line.lower() for k in ("roulette", "claim", "rank", "like", "kakera"))
            and not re.search(r"\b\d{17,20}\b", first_line)
        ):
            if first_line.lower() != char_name.lower():
                series = first_line
            else:
                logger.debug("Series line equals character name — will handle as self-titled later.")

    # --- Kakera extraction (multi-pass) ---
    kakera_patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*[💎♦]',
        r'[💎♦]\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*<:kakera:',
        r'roulette\s*[•-]?\s*(\d{1,3}(?:,\d{3})*)'
    ]
    for pat in kakera_patterns:
        m = re.search(pat, desc, re.IGNORECASE)
        if m:
            kakera_value = _parse_int_with_commas(m.group(1))
            break

    if kakera_value is None:
        pos = desc.find("💎") if "💎" in desc else desc.find("♦")
        if pos != -1:
            snippet = desc[max(0, pos - 30):pos + 30]
            nums = re.findall(r'(\d{1,3}(?:,\d{3})*|\d{1,4})', snippet)
            for n in nums:
                val = _parse_int_with_commas(n)
                if val and 10 <= val <= 50000:
                    kakera_value = val
                    break

    # --- Claim & Like ranks ---
    match_claim = re.search(r"Claim\s*Rank\s*:\s*#?\s*([\d,]+)", desc, re.IGNORECASE)
    match_like = re.search(r"Like\s*Rank\s*:\s*#?\s*([\d,]+)", desc, re.IGNORECASE)
    if match_claim:
        claim_rank = _parse_int_with_commas(match_claim.group(1))
    if match_like:
        like_rank = _parse_int_with_commas(match_like.group(1))

    # --- Fallback: self-titled or misparsed ---
    if not series or not re.search(r"[A-Za-z]", series):
        series = char_name
        logger.debug("Fallback to self-titled series for: %r", char_name)

    # --- Sanity: skip clearly invalid embeds ---
    if not char_name or not series or not re.search(r"[A-Za-z]", char_name):
        logger.debug("Rejected invalid or empty embed: %r | %r", char_name, series)
        return {"name": None, "series": None, "kakera_value": None, "claim_rank": None, "like_rank": None}

    # --- Log final parse result ---
    logger.info(
        f"🎯 Parsed $im → Name='{char_name}', Series='{series}', "
        f"Kakera={kakera_value}, ClaimRank={claim_rank}, LikeRank={like_rank}"
    )

    return {
        "name": char_name.strip(),
        "series": series.strip(),
        "kakera_value": kakera_value,
        "claim_rank": claim_rank,
        "like_rank": like_rank,
    }
