"""thesis_corpus_overrides.py — user-editable single-char override template.

Like ``thesis_phrase_overrides.py`` but for SINGLE characters. Use this
to declare "for this Bopomofo, prefer THIS character" overrides that
beat the engine's built-in frequency ranking.

Auto-generate from your corpus with:

    python tests/build_char_overrides.py --corpus /path/to/your/text/dir

Format: Bopomofo (with tone marks) → single Traditional Chinese char.

Note: this file is intentionally MOSTLY EMPTY in the public template,
because the built-in frequency ranking + Top-200/500 boost + CC-EDICT
phrase coverage already gets ~90% accuracy on real Traditional text.
Only add entries here for chars where you've observed mistranslations
specific to your domain.
"""
from __future__ import annotations

THESIS_CORPUS_OVERRIDES: dict[str, str] = {
    # ── Examples (delete or replace with your own) ──
    # Format: 'Bopomofo': '單字'
    # 'ㄒㄧㄣ': '新',  # if you write much more 新 than 心
    # 'ㄓㄥ': '徵',    # if your domain uses 徵 (e.g., research papers)
}
