# src/bot/utils/normalization.py
import re
import unicodedata
from typing import Optional

def normalize_text(text: Optional[str]) -> str:
    """
    Conservative normalization for names (keeps punctuation that may be part of names).
    Purpose: used for name_normalized (character names).
    """
    if not text:
        return ""
    s = str(text).strip()
    s = unicodedata.normalize("NFKC", s)  # normalize Unicode forms
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_series_loose(series: Optional[str]) -> str:
    """
    Looser series normalizer used for the DB key:
    - Lowercases
    - Normalizes Unicode
    - Removes trailing 'wo', 'を', trailing punctuation like '!' and repeated spaces
    - Collapses several small punctuation differences
    This function is designed to make "Kono Subarashii Sekai ni Shukufuku wo!" and
    "Kono Subarashii Sekai ni Shukufuku" normalize to the SAME string.
    """
    if not series:
        return "unknown"

    s = str(series).strip()
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()

    # Replace punctuation characters that commonly vary with a single space,
    # but keep colons and some separators inside names (if you prefer to keep colons,
    # remove ":" from the bracket below).
    s = re.sub(r"[\/\\\(\)\[\]\{\},;\"’‘\*\+\?·••·:]", " ", s)

    # Normalize various dashes to hyphen
    s = s.replace("—", "-").replace("–", "-")

    s = re.sub(r"\s+", " ", s).strip()

    # Remove trailing Japanese particle "wo" or "を" optionally followed by punctuation/spaces
    s = re.sub(r"(?:\bwo\b|\bを\b)[\s!！]*$", "", s)

    # Remove trailing exclamation/question marks (space handled above)
    s = re.sub(r"[!！\?？]+$", "", s)

    s = s.strip()
    return s
