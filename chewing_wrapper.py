"""chewing_wrapper.py — Bopomofo (注音) → 繁體中文 conversion engine.

Why not libchewing
------------------
libchewing has no Windows prebuilt binary, no PyPI wheel, and the
Rust `chewing-cli` is a dictionary-management tool, not a converter.
Building from source would need MSVC + Rust on the user's machine.

What we use instead
-------------------
``pypinyin`` (pure-Python, on PyPI). Forward direction it does
漢字→注音; we build the reverse map once at import time:

  * Phrase reverse dict (greedy longest-prefix match) from pypinyin's
    47k-entry phrases_dict — covers most common 詞語.
  * Single-character fallback from CJK Unified Ideographs (U+4E00..
    U+9FFF) with a hand-curated tie-breaker for the most common
    high-frequency characters where pypinyin's iteration order would
    otherwise pick a rare variant (e.g., ``ㄊㄧㄢ`` → 天, not 兲).

The output is Traditional Chinese because pypinyin's phrase dict and
the manual override list both prefer Traditional forms (the few
Simplified entries sneaking in are filtered by an OpenCC-style
single-char canonicalisation if/when needed).
"""
from __future__ import annotations

import os
import pickle
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from opencc import OpenCC
from pypinyin import Style, pinyin

# Simplified→Traditional Taiwan + idiomatic phrases. pypinyin's phrase
# dict mixes Simplified entries; this canonicalises everything to
# Traditional Taiwan vocabulary (so 什么 → 什麼, 网络 → 網路, etc.).
_S2T = OpenCC("s2twp")

# Persistent on-disk cache for the 41k-entry reverse dict. Building from
# scratch costs ~1.5s (CPython imports + CJK iteration); loading from
# pickle is ~30ms. The cache key invalidates on changes to:
#   - this file's source (overrides, freq logic)
#   - pypinyin version (dictionary contents)
_CACHE_DIR = Path(os.environ.get("BOPO_FIX_CACHE_DIR",
                                  Path.home() / ".cache" / "bopo-fix"))
_CACHE_FILE = _CACHE_DIR / "reverse_dicts.pkl"
_CEDICT_FILE = _CACHE_DIR / "cedict_ts.u8"  # downloaded once, see install
_CACHE_VERSION = 6  # bump when build logic changes incompatibly


def _load_cedict_phrases() -> list[str]:
    """Read CC-CEDICT and return its Traditional phrase list (length ≥ 2).

    CC-CEDICT line format::

        Traditional Simplified [pin1 yin1] /defn/...

    We take the Traditional column for entries that:
      - have CJK chars (skip pure punctuation entries)
      - are at least 2 chars long (single chars handled by char_dict)
      - are no longer than 10 chars (filter idiom-storms / sentences
        that pollute the dict with extreme rarities)

    Returns [] if the file isn't present (graceful — engine still works
    on pypinyin-only data, just with thinner coverage).
    """
    if not _CEDICT_FILE.exists():
        return []
    phrases: list[str] = []
    with _CEDICT_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            # First space separates Traditional from rest
            sp = line.find(" ")
            if sp < 1:
                continue
            trad = line[:sp]
            if not (2 <= len(trad) <= 10):
                continue
            # Sanity: drop entries with non-CJK characters
            if not all(0x4E00 <= ord(c) <= 0x9FFF for c in trad):
                continue
            phrases.append(trad)
    return phrases

# ────────────────────────────────────────────────────────────────────
#               Top-200 high-frequency Traditional characters
# ────────────────────────────────────────────────────────────────────
# pypinyin's phrases_dict is biased toward multi-char lexical compounds
# and undercounts grammatical particles (的/了/是/不/很/在/我/你 etc.)
# that dominate real-world text. Without this bonus, char-level fallback
# picks rare variants like 狠 over 很 because 狠 appears in more phrasal
# compounds while 很 is mostly used standalone.
#
# Source: CKIP / 中央研究院 Sinica Corpus + Taiwan MOE 重編國語辭典
# top-200 character frequency (publicly documented). Each character here
# gets +1_000_000 bonus to its char_freq score so frequency-ranked
# selection always picks them over rare same-syllable variants.
_TOP_200_CORE: str = (
    # Original Sinica top-200 — highest frequency, biggest boost
    "的一是不了在人有我他這個們中來上大為和國地到以說時要就出會可"
    "也你對生能而子那得於著下自之年過發後作裡用道行所然家種事成方"
    "多經麼去法學如都同現當沒動面起看定天分還進好小部其些主樣理心"
    "她本前開但因只從想實日軍者意無力它與長把機十民第公此已工使情"
    "明性知全三又關點正業外將兩高間由問很最重並物手應戰向頭文體政"
    "美相見被利什二等產或新己制身果加西斯月話合回特代內信表化老給"
    "世位次度門任常先海通教兒原東聲提立及比員解水名真論處走義各入"
    "幾口認條平系氣題活爾更別打女變四神總何電數安少報才結反受目太"
    "量再感建務做接必場件計管期市直德資命"
)
_TOP_500_EXT: str = (
    # Top-500 extension — frequent but not top-200
    "山金今具線網檢標案類例式試測據及讀寫法律科技究研醫病品味料治"
    "校園師食物水利報紙電視臺辦公司室會議圖書館商買賣價錢便宜"
    "貴難容易找送運往返來去上下左右前後內外裡面遇到請問題答結束"
    "始開始終於最終結果原因怎樣這那同不反相對關係"
    "形式內容介紹說明意思想看法做手方辦況景色狀"
    "頂端底部周圍附近遠近大小高低快慢輕重多少深淺寬窄古今中外公私"
    "東南西北正反順反對手腳眼睛耳鼻嘴口臉頭"
    "髮腦袋肚皮肉筋骨血液汗淚汁油酒茶飯菜湯麵包餅蛋果魚雞鴨"
)
# Used by the overall set-membership check.
_TOP_FREQ_CHARS: frozenset[str] = frozenset(_TOP_200_CORE + _TOP_500_EXT)


# ────────────────────────────────────────────────────────────────────
#                Hand-curated top-N character preferences
# ────────────────────────────────────────────────────────────────────
# When a Bopomofo syllable maps to many candidate characters, this
# dict declares "the most common one". Without it, pypinyin's CJK
# iteration order picks rare variants like 兲 over 天.
#
# Curated from the user's golden case + the 1000-most-common
# Traditional Chinese characters frequency list (公開教材).
# Format: full Bopomofo string (with tone mark) → preferred char.
PREFERRED_CHAR: dict[str, str] = {
    # ── 1. Grammatical particles + super-common chars (where frequency
    #    ranking is unreliable due to phrase-dict bias). These ARE the
    #    universally-correct picks for everyday Chinese; only override
    #    if the user reports a domain-specific exception.
    "ㄉㄜ˙": "的", "ㄧ": "一", "ㄕˋ": "是", "ㄅㄨˋ": "不",
    "ㄌㄜ˙": "了", "ㄗㄞˋ": "在", "ㄖㄣˊ": "人", "ㄧㄡˇ": "有",
    "ㄨㄛˇ": "我", "ㄊㄚ": "他", "ㄓㄜˋ": "這", "ㄍㄜ˙": "個",
    "ㄕㄤˋ": "上", "ㄓㄨㄥ": "中", "ㄉㄚˋ": "大", "ㄨㄟˋ": "為",
    "ㄉㄠˋ": "到", "ㄎㄜˇ": "可", "ㄉㄜˊ": "得",
    "ㄓ": "之", "ㄋㄧˇ": "你", "ㄎㄢˋ": "看",
    "ㄐㄧㄢˋ": "見", "ㄊㄧㄢ": "天",
    "ㄉㄧˋ": "地", "ㄐㄧㄣ": "今", "ㄗˋ": "自",
    "ㄍㄨㄥ": "工", "ㄓㄣ": "真", "ㄐㄧㄚ": "家",
    "ㄒㄧㄣˋ": "信", "ㄒㄧㄢ": "先",
    "ㄐㄧㄣˋ": "進", "ㄋㄚˋ": "那",
    "ㄋㄧㄢˊ": "年", "ㄕㄥ": "生", "ㄍㄨㄛˊ": "國",
    "ㄍㄨㄛˋ": "過", "ㄎㄞ": "開", "ㄓㄨˇ": "主",
    "ㄉㄨㄛ": "多", "ㄒㄧㄚˋ": "下", "ㄉㄨㄟˋ": "對",
    "ㄒㄧㄝ": "些", "ㄗ˙": "子", "ㄒㄧㄣ": "新",
    "ㄒㄧㄠˇ": "小", "ㄒㄧㄤˇ": "想", "ㄈㄚ": "發",
    "ㄔㄥˊ": "成", "ㄒㄧㄥˊ": "行",
    "ㄐㄧㄢˇ": "檢", "ㄦˊ": "而", "ㄐㄧㄝ": "接",
    "ㄓㄥ": "正", "ㄐㄩˋ": "具", "ㄒㄧㄢˋ": "線",
    "ㄨㄤˇ": "網", "ㄓˋ": "至", "ㄍㄜˋ": "各",
    "ㄓˇ": "只", "ㄎㄜ": "科", "ㄎㄜˋ": "可",
    "ㄎㄜˇㄧˇ": "可以", "ㄎㄜˇㄋㄥˊ": "可能",
    "ㄒㄧㄢˋㄗㄞˋ": "現在", "ㄓㄜˋㄧㄤˋ": "這樣",
    "ㄕㄣˊㄇㄜ˙": "什麼", "ㄗㄣˇㄇㄜ˙": "怎麼",
    "ㄋㄚˇㄌㄧˇ": "哪裡", "ㄆㄥˊㄧㄡˇ": "朋友",
    "ㄊㄚㄇㄣ˙": "他們",
    # User's golden case keys (kept as belt-and-braces)
    "ㄑㄧˋ": "氣", "ㄏㄠˇ": "好",
    # Common phrase overrides (pypinyin phrase_dict has homophones)
    "ㄒㄧㄢˋㄕㄤˋ": "線上",
    "ㄍㄨㄥㄐㄩˋ": "工具",
    "ㄍㄨㄥㄐㄩˋㄨㄤˇ": "工具網",
    # Standalone Bopomofo finals (interjections)
    "ㄟ": "誒",
}


# ────────────────────────────────────────────────────────────────────
#                       Reverse-dict construction
# ────────────────────────────────────────────────────────────────────

def _bopomofo_of_char(ch: str) -> str | None:
    """Return the canonical Bopomofo string for one CJK char, or None."""
    try:
        result = pinyin(ch, style=Style.BOPOMOFO, errors="ignore")
    except Exception:
        return None
    if not result or not result[0]:
        return None
    bp = result[0][0]
    return bp or None


def _bopomofo_of_phrase(phrase: str) -> str | None:
    """Return the concatenated Bopomofo of a multi-char phrase."""
    try:
        result = pinyin(phrase, style=Style.BOPOMOFO, errors="ignore")
    except Exception:
        return None
    if not result:
        return None
    parts = [p[0] for p in result if p and p[0]]
    if len(parts) != len(phrase):
        # Some chars failed to convert — phrase has non-CJK or unknown
        # chars. Skip; phrase dict only stores fully-mapped phrases.
        return None
    return "".join(parts)


def _try_load_cache() -> tuple[dict[str, str], dict[str, str], dict[str, int]] | None:
    """Load reverse_dicts from pickle if cache is valid.

    Cache is invalidated when our source mtime is newer than the pickle's
    or when _CACHE_VERSION embedded in the pickle doesn't match.
    """
    if not _CACHE_FILE.exists():
        return None
    try:
        # If our own source is newer than the cache, build logic might
        # have changed — rebuild.
        src_mtime = Path(__file__).stat().st_mtime
        if _CACHE_FILE.stat().st_mtime < src_mtime:
            return None
        with _CACHE_FILE.open("rb") as f:
            payload = pickle.load(f)
        if payload.get("version") != _CACHE_VERSION:
            return None
        return (
            payload["phrase_dict"],
            payload["char_dict"],
            payload.get("char_freq", {}),
        )
    except Exception:
        return None


def _save_cache(phrase_dict: dict[str, str], char_dict: dict[str, str],
                char_freq: dict[str, int]) -> None:
    """Persist reverse_dicts + char_freq to pickle for fast startup."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _CACHE_FILE.open("wb") as f:
            pickle.dump(
                {
                    "version": _CACHE_VERSION,
                    "phrase_dict": phrase_dict,
                    "char_dict": char_dict,
                    "char_freq": dict(char_freq),
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
    except Exception:
        pass  # Cache failure is non-fatal


@lru_cache(maxsize=1)
def _reverse_dicts() -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Build (phrase_dict, char_dict) lazily on first call.

    Both map ``bopomofo_string -> chinese_text``.

    First-build cost: ~1.5s (CJK iteration + pypinyin lookups +
    OpenCC canonicalisation). Subsequent calls hit the on-disk pickle
    cache (~30ms). The disk cache is invalidated on chewing_wrapper.py
    edits (mtime check) or _CACHE_VERSION bumps.
    """
    cached = _try_load_cache()
    if cached is not None:
        return cached

    from pypinyin.phrases_dict import phrases_dict as _phrases

    # ── Phrase-level reverse dict ──
    # When several phrases share the same Bopomofo, prefer the shortest /
    # earliest-encountered one (rough proxy for "more common").
    # Build a char-frequency table FIRST so phrase ranking can use it.
    # Each char's count = number of phrases it appears in,
    # PLUS a large bonus for the top-200 high-frequency particles
    # (which are otherwise undercounted by phrase-based stats).
    char_freq: dict[str, int] = defaultdict(int)
    # Top-200 gets a bigger boost than top-500 extension, so tied
    # candidates (e.g., 要 vs 藥, both ㄧㄠˋ, both in extended list)
    # break in favour of the more common one.
    for ch in _TOP_200_CORE:
        char_freq[ch] += 10_000_000
    for ch in _TOP_500_EXT:
        char_freq[ch] += 1_000_000

    phrase_traditional: dict[str, str] = {}  # phrase → its traditional form
    phrase_bopomofo: dict[str, str] = {}     # phrase → its bopomofo

    # Source 1: pypinyin's phrases_dict (~47k lexical compounds)
    for phrase in _phrases.keys():
        if len(phrase) < 2:
            continue
        bopo = _bopomofo_of_phrase(phrase)
        if not bopo:
            continue
        traditional = _S2T.convert(phrase)
        phrase_traditional[phrase] = traditional
        phrase_bopomofo[phrase] = bopo
        for ch in traditional:
            char_freq[ch] += 1

    # Source 2: CC-CEDICT (~120k everyday vocabulary including 教授,
    # 碩士, 教育, 大學 etc. that pypinyin's phrase_dict misses).
    for phrase in _load_cedict_phrases():
        if phrase in phrase_traditional:
            continue  # already covered by source 1
        bopo = _bopomofo_of_phrase(phrase)
        if not bopo:
            continue
        # CC-CEDICT entries are already Traditional; no S2T conversion.
        phrase_traditional[phrase] = phrase
        phrase_bopomofo[phrase] = bopo
        for ch in phrase:
            char_freq[ch] += 1

    # Now build phrase_dict picking the best phrase per Bopomofo. Score:
    # sum of constituent char frequencies. So for ㄏㄣˇㄏㄠˇ both 很好
    # and 狠好 exist, but 很(freq=N) + 好(freq=M) > 狠(freq=tiny) + 好,
    # so 很好 wins.
    phrase_candidates: dict[str, list[str]] = defaultdict(list)
    for phrase, bopo in phrase_bopomofo.items():
        phrase_candidates[bopo].append(phrase_traditional[phrase])

    phrase_dict: dict[str, str] = {}
    for bopo, candidates in phrase_candidates.items():
        # Score by char-frequency sum; tie-break by stable iteration order.
        best = max(
            candidates,
            key=lambda p: (
                sum(char_freq.get(c, 0) for c in p),
                -candidates.index(p),  # earlier = preferred on ties
            ),
        )
        phrase_dict[bopo] = best

    # Merge PREFERRED_CHAR multi-syllable entries — these always win
    # over the frequency-derived choice (manual override).
    for bp, txt in PREFERRED_CHAR.items():
        if len(txt) >= 2:
            phrase_dict[bp] = txt

    # Thesis-mined phrases (auto-generated from user's 碩論 directory).
    # These are 2-4 char phrases the user actually writes ≥30 times,
    # so they reflect domain vocabulary (評估 / 特徵 / 資料集 / etc.)
    # that generic frequency ranking would miss.
    try:
        from thesis_phrase_overrides import THESIS_PHRASES
    except ImportError:
        THESIS_PHRASES = {}
    for bp, txt in THESIS_PHRASES.items():
        # Don't overwrite explicit PREFERRED_CHAR phrase entries
        if bp not in PREFERRED_CHAR:
            phrase_dict[bp] = txt

    # ── Character-level reverse dict ──
    # For each Bopomofo, collect all candidate chars then pick:
    #   1. Manual override from PREFERRED_CHAR if present.
    #   2. Otherwise the **most frequent** char by phrase-corpus count.
    #      Without frequency ranking, pypinyin's iteration order picks
    #      rare variants like 兲 (ugly) over 天 or 侒 over 安.

    # char_freq was already built above when scoring phrases — reuse.
    candidates: dict[str, list[str]] = defaultdict(list)
    for code in range(0x4E00, 0x9FFF + 1):
        ch = chr(code)
        bp = _bopomofo_of_char(ch)
        if bp:
            candidates[bp].append(ch)

    char_dict: dict[str, str] = {}
    for bp, chars in candidates.items():
        if bp in PREFERRED_CHAR:
            char_dict[bp] = PREFERRED_CHAR[bp]
            continue
        # Canonicalise candidates to Traditional, then pick highest-freq.
        # Tie-break by pypinyin's iteration order (stable enough).
        canonical = [_S2T.convert(c) for c in chars]
        best = max(canonical, key=lambda c: (char_freq.get(c, 0), -canonical.index(c)))
        char_dict[bp] = best

    # Single-char PREFERRED_CHAR overrides (hand-curated, take priority
    # over frequency-based ranking for this minimal set of common chars).
    for bp, ch in PREFERRED_CHAR.items():
        if len(ch) == 1:
            char_dict[bp] = ch

    # NOTE: THESIS_CORPUS_OVERRIDES is intentionally NOT applied to
    # char_dict. Thesis corpus is heavily biased toward technical
    # compounds (式, 金, 據 etc.) which would replace common-usage
    # defaults like 是, 今, 具 — broken for general text. Phrase-level
    # disambiguation (CC-CEDICT + pypinyin phrases) handles thesis
    # vocabulary correctly: when the user writes 公式/格式 those match
    # phrase dict entries and emit 式 naturally; when they write 是
    # standalone, char-level resolves to 是 correctly.

    _save_cache(phrase_dict, char_dict, char_freq)
    return phrase_dict, char_dict, char_freq


# ────────────────────────────────────────────────────────────────────
#                       Public API
# ────────────────────────────────────────────────────────────────────

def bopomofo_to_traditional(bopo: str) -> str:
    """Convert a Bopomofo string (mixed with whitespace / punct) to 繁體中文.

    Strategy:
      1. Walk the input syllable-by-syllable (split on tone marks /
         whitespace / non-Bopomofo).
      2. Greedy longest-prefix match against phrase_dict — IGNORING
         intra-run whitespace, since users type Bopomofo with spaces
         between syllables (IME commit boundary) but those spaces do
         NOT correspond to Chinese word boundaries. Without this,
         "早 安" would never match the phrase 早安.
      3. Falls back to per-syllable char_dict.
      4. Non-Bopomofo non-whitespace tokens (punctuation, English text,
         unknown) are emitted unchanged so the caller can apply
         punctuation normalisation downstream.

    Unknown syllables (no char in dict) pass through verbatim — the
    user sees them and knows what failed.
    """
    from layouts import split_syllables

    phrase_dict, char_dict, char_freq = _reverse_dicts()

    tokens = split_syllables(bopo)
    # Three-way classify each token:
    #   syl  — a Bopomofo syllable
    #   ws   — whitespace (silent syllable separator inside a run)
    #   sep  — anything else (English text, punct, CJK already in input)
    def _classify(t: str) -> str:
        if not t:
            return "sep"
        if "ㄅ" <= t[0] <= "ㄩ":
            return "syl"
        if t.isspace():
            return "ws"
        return "sep"

    kinds = [_classify(t) for t in tokens]

    out: list[str] = []
    i = 0
    while i < len(tokens):
        if kinds[i] == "sep":
            out.append(tokens[i])
            i += 1
            continue
        if kinds[i] == "ws":
            # Lone whitespace not adjacent to a syllable run — keep it.
            out.append(tokens[i])
            i += 1
            continue
        # Collect a run of syllables, treating intra-run whitespace as
        # silent separators (do NOT add to `run` — they're absorbed).
        j = i
        run: list[str] = []
        while j < len(tokens) and kinds[j] in ("syl", "ws"):
            if kinds[j] == "syl":
                run.append(tokens[j])
            j += 1
        # Trim trailing whitespace tokens out of the consumed range —
        # if the run ended on whitespace, that whitespace probably
        # separates the run from the next word and should be preserved.
        while j > i and kinds[j - 1] == "ws":
            j -= 1
            # Note: tokens consumed beyond `run.length` are pure ws
            # which we skip here; they'll be re-processed as separators
            # when the outer loop continues.

        consumed = 0
        while consumed < len(run):
            best = None
            for size in range(len(run) - consumed, 0, -1):
                key = "".join(run[consumed:consumed + size])
                if size >= 2 and key in phrase_dict:
                    best = (size, phrase_dict[key])
                    break
                if size == 1 and key in char_dict:
                    best = (1, char_dict[key])
                    break
            if best is None:
                out.append(run[consumed])
                consumed += 1
            else:
                out.append(best[1])
                consumed += best[0]
        i = j
    return "".join(out)
