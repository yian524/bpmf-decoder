"""thesis_phrase_overrides.py — user-editable phrase override template.

This file ships as a small **template** with example entries. The intent
is that you either:

  1. Edit this file by hand to add specific phrases you care about
     (Bopomofo string → Traditional Chinese phrase), OR

  2. Auto-generate it from your own corpus (papers, blog posts, notes)
     by running:

        python tests/build_phrase_overrides.py --corpus /path/to/your/text/dir

     The generator will scan all .md/.txt files in that directory,
     extract phrases of length 2-4 that appear ≥ 30 times, and rewrite
     this file with the mined phrase list.

Without entries here, the engine still works — it falls back to
CC-CEDICT (122k entries) + pypinyin's phrase dict (47k entries) for
phrase coverage. This file just tunes for your domain-specific
vocabulary.

Format: Bopomofo (with tone marks) → Traditional Chinese phrase string.
Bopomofo can be obtained via:

    from pypinyin import pinyin, Style
    "".join(p[0] for p in pinyin("你的詞", style=Style.BOPOMOFO))
"""
from __future__ import annotations

THESIS_PHRASES: dict[str, str] = {
    # ── Examples (delete or replace with your own) ──
    # Format: 'Bopomofo string': 'Traditional Chinese phrase'
    "ㄗㄌㄧㄠˋ": "資料",
    "ㄕˊㄧㄢˋ": "實驗",
    "ㄌㄨㄣˋㄨㄣˊ": "論文",
    "ㄧㄢˊㄐㄧㄡˋ": "研究",
    "ㄈㄤㄈㄚˇ": "方法",
    "ㄐㄧㄝˊㄍㄨㄛˇ": "結果",
    "ㄈㄣㄒㄧ": "分析",
    "ㄐㄧㄠˋㄕㄡˋ": "教授",
    "ㄕㄨㄛˋㄕˋ": "碩士",
    "ㄕㄣㄉㄨˋㄒㄩㄝˊㄒㄧˊ": "深度學習",
    # Add your own entries below, or run the generator to populate
    # automatically from a corpus you provide.
}
