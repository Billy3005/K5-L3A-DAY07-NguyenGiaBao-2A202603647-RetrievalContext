"""Text normalization copied verbatim from Day 6 (starter/src/ingestion.py) so that the
hit definition is identical across Day 6 and Day 7."""
import re
import unicodedata

_CHAR_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "­": "", "​": "", "﻿": "",
})


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_CHAR_MAP)
    return re.sub(r"\s+", " ", text).strip()


def match_key(text: str) -> str:
    """Canonical form for evidence matching: normalized, whitespace-collapsed, lowercase."""
    return normalize_text(text).lower()
