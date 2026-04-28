"""layouts.py — English keyboard key → Bopomofo symbol mapping.

Source of truth for the 大千 (Standard / Dachen) layout: libchewing's Rust
source at `src/editor/zhuyin_layout/standard.rs` (LGPL-2.1, transcribed
by hand from upstream). Verified against user's golden cases, e.g.:

    rup → ㄐㄧㄣ → 今
    cl3 → ㄏㄠˇ → 好
    vu04 → ㄒㄧㄢˋ → 線

V1 ships only the 大千 layout (the Microsoft Bopomofo IME default in
Taiwan). Adding 倚天 / Hsu / IBM later means adding a new dict below
and switching by `LAYOUT` constant.
"""
from __future__ import annotations

# ────────────────────────────────────────────────────────────────────
#                 大千 (Standard / Dachen) layout
# ────────────────────────────────────────────────────────────────────
# Bopomofo symbols (37) + tone marks (4 — 第一聲 is implicit / no mark).
# Key string is what the user's keyboard literally types when the
# Bopomofo IME is OFF and they type "as if" Bopomofo were on.
DACHEN: dict[str, str] = {
    # number row
    "1": "ㄅ", "2": "ㄉ", "3": "ˇ", "4": "ˋ", "5": "ㄓ",
    "6": "ˊ", "7": "˙", "8": "ㄚ", "9": "ㄞ", "0": "ㄢ", "-": "ㄦ",
    # qwerty row
    "q": "ㄆ", "w": "ㄊ", "e": "ㄍ", "r": "ㄐ", "t": "ㄔ",
    "y": "ㄗ", "u": "ㄧ", "i": "ㄛ", "o": "ㄟ", "p": "ㄣ",
    # asdf row
    "a": "ㄇ", "s": "ㄋ", "d": "ㄎ", "f": "ㄑ", "g": "ㄕ",
    "h": "ㄘ", "j": "ㄨ", "k": "ㄜ", "l": "ㄠ", ";": "ㄤ",
    # zxcv row
    "z": "ㄈ", "x": "ㄌ", "c": "ㄏ", "v": "ㄒ", "b": "ㄖ",
    "n": "ㄙ", "m": "ㄩ", ",": "ㄝ", ".": "ㄡ", "/": "ㄥ",
}

# Available layouts. Add 'eten', 'hsu', 'ibm' here in v2.
LAYOUTS: dict[str, dict[str, str]] = {
    "dachen": DACHEN,
    "standard": DACHEN,  # alias
}

# Tone marks set, used to detect syllable boundaries during segmentation.
TONE_MARKS: frozenset[str] = frozenset({"ˊ", "ˇ", "ˋ", "˙"})


def english_to_bopomofo(text: str, layout: str = "dachen") -> str:
    """Translate raw English-key text to a Bopomofo + tone-marker stream.

    Lower-cases ASCII letters (Bopomofo IME ignores Shift on letter keys —
    Shift+letter is treated identically to letter).

    Characters not in the layout (e.g., spaces, CJK punctuation, or letters
    typed with the IME's English mode) pass through unchanged so the caller
    can preserve formatting / split phrases on whitespace.

    Punctuation heuristic
    ---------------------
    `,` and `.` are special: in the Dachen layout they map to ㄝ and ㄡ
    (Bopomofo finals used in 業/葉/些/流/牛/球 etc.), but they're also
    standard sentence punctuation. In wrong-IME-garble scenarios users
    typically type them as punctuation, not as Bopomofo finals.

    Heuristic: look at the PREVIOUS character (in the original input):
      - If it's a Bopomofo medial key (`u`=ㄧ, `j`=ㄨ, `m`=ㄩ) or for
        `.` also a vowel/initial that could plausibly precede ㄡ
        (we accept any letter), treat as Bopomofo final.
      - Otherwise (start of string, or following a tone digit / space /
        another punctuation), treat as ASCII sentence punctuation.

    Why prev-char not next-char: ㄝ is ALWAYS a final and MUST follow
    a medial (ㄧㄝ ㄨㄝ ㄩㄝ). ㄡ similarly: as a final follows a
    medial; as a standalone syllable (歐) it's at start-of-syllable
    so won't have a Bopomofo letter before it. Checking what's BEFORE
    is therefore unambiguous; checking what's AFTER (next char) is
    fooled by trailing whitespace between syllables.
    """
    table = LAYOUTS.get(layout)
    if table is None:
        raise ValueError(f"unknown layout: {layout!r}; choose from {sorted(LAYOUTS)}")

    # Tone digits (3/4/6/7) END a syllable in Bopomofo IME — anything
    # after them starts a new syllable OR is sentence-level punct.
    # The number-row keys 1/2/5/8/9/0/- are Bopomofo *letters* (B/D/Z/A/
    # AI/AN/ER), so a `,` after one of them IS mid-syllable.
    _TONE_DIGITS = set("3467")
    _BOPO_LETTERS_DIGITS = set("12589") | {"0", "-"}
    # `,` / `.` is treated as Bopomofo final iff prev key is:
    #   - a Bopomofo letter (a-z), OR
    #   - a Bopomofo number-row letter (1/2/5/8/9/0/-).
    # Otherwise (start, whitespace, tone digit, or another punct), it
    # acts as ASCII sentence punctuation.
    _PREV_MEANS_BOPO = (
        set("abcdefghijklmnopqrstuvwxyz") | _BOPO_LETTERS_DIGITS
    )

    out: list[str] = []
    for i, ch in enumerate(text):
        lower = ch.lower()
        if lower in (",", "."):
            prev_ch = text[i - 1].lower() if i > 0 else ""
            if prev_ch in _PREV_MEANS_BOPO:
                # Mid-syllable → Bopomofo final ㄝ / ㄡ.
                out.append(table[lower])
            else:
                # Start of input, or after whitespace / tone digit /
                # another punct → ASCII sentence punctuation.
                out.append(ch)
            continue
        out.append(table.get(lower, ch))
    return "".join(out)


def split_syllables(bopo: str) -> list[str]:
    """Split a Bopomofo stream into syllables on tone-mark boundaries.

    Each syllable is the run of Bopomofo letters up to and including its
    tone mark. The implicit first-tone (no mark) is delimited by whitespace
    or by a non-Bopomofo character — those become their own tokens.

    Example::

        split_syllables("ㄐㄧㄣ ㄊㄧㄢ ㄑㄧˋㄓㄣ ㄏㄠˇ!")
        → ["ㄐㄧㄣ", " ", "ㄊㄧㄢ", " ", "ㄑㄧˋ", "ㄓㄣ", " ", "ㄏㄠˇ", "!"]
    """
    out: list[str] = []
    buf: list[str] = []
    for ch in bopo:
        is_bopo_letter = "ㄅ" <= ch <= "ㄩ"  # ㄅ..ㄩ range
        if is_bopo_letter:
            buf.append(ch)
        elif ch in TONE_MARKS:
            buf.append(ch)
            out.append("".join(buf))
            buf = []
        else:
            # Non-Bopomofo char (whitespace, punct) breaks the current
            # syllable (= implicit first-tone) and is emitted as its own
            # token.
            if buf:
                out.append("".join(buf))
                buf = []
            out.append(ch)
    if buf:
        out.append("".join(buf))
    return out
