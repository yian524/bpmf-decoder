"""punct.py — half-width ASCII punctuation → CJK full-width punctuation.

Applied after chewing conversion so that ``rup wu0 wu0 fu4 5p cl3!``
ends as ``今天天氣真好！`` (note 全形 ！) rather than half-width ``!``.

Conservative table — only converts characters that are unambiguously
"sentence-end punctuation" in Chinese context. Quote handling (``"``
``'``) is intentionally left alone in v1: deciding between 「」 / 『』 /
"" needs context (open vs close, single vs double level) which we
don't track.
"""
from __future__ import annotations

# Half-width → full-width mapping. Only characters whose Chinese
# convention is unambiguous appear here.
_PUNCT_MAP: dict[str, str] = {
    "!": "！",
    "?": "？",
    ",": "，",
    ".": "。",
    ";": "；",
    ":": "：",
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
    "<": "〈",
    ">": "〉",
    "~": "～",
}


def apply_chinese_punctuation(text: str) -> str:
    """Convert ASCII punctuation to its CJK full-width counterpart.

    Operates char-by-char. Non-target characters pass through unchanged
    (CJK characters, ASCII letters, digits, whitespace, quotes).

    Idempotent: running twice gives the same result, since CJK
    full-width punctuation is not in ``_PUNCT_MAP`` keys.
    """
    return "".join(_PUNCT_MAP.get(ch, ch) for ch in text)
