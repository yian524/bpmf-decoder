"""Unit tests for layouts.english_to_bopomofo + split_syllables.

Golden cases verified against libchewing's standard.rs source for the
Dachen layout. Any divergence between this test and libchewing means
the table got desynced from upstream — fix layouts.py, not the test.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest

from layouts import (
    DACHEN,
    TONE_MARKS,
    english_to_bopomofo,
    split_syllables,
)


# ============================================================
# 1. Per-key mapping (every key in DACHEN has a unique bopomofo)
# ============================================================

class TestDachenTable:
    def test_table_has_41_entries(self):
        # 37 Bopomofo + 4 tone marks = 41
        assert len(DACHEN) == 41

    def test_all_values_unique(self):
        """No two keys should map to the same Bopomofo (would be IME nonsense)."""
        values = list(DACHEN.values())
        assert len(values) == len(set(values)), \
            f"duplicate values in DACHEN: {[v for v in values if values.count(v) > 1]}"

    def test_tone_marks_present(self):
        for mark in ("ˊ", "ˇ", "ˋ", "˙"):
            assert mark in DACHEN.values(), f"missing tone mark: {mark}"

    def test_tone_marks_constant_matches_table(self):
        in_table = {v for v in DACHEN.values() if v in ("ˊ", "ˇ", "ˋ", "˙")}
        assert in_table == set(TONE_MARKS)


# ============================================================
# 2. Spot-check libchewing-defined keys
# ============================================================

class TestKnownMappings:
    """These came directly from libchewing/src/editor/zhuyin_layout/standard.rs."""

    @pytest.mark.parametrize("key,expected", [
        # number row
        ("1", "ㄅ"), ("2", "ㄉ"), ("3", "ˇ"), ("4", "ˋ"), ("5", "ㄓ"),
        ("6", "ˊ"), ("7", "˙"), ("8", "ㄚ"), ("9", "ㄞ"), ("0", "ㄢ"),
        ("-", "ㄦ"),
        # qwerty row
        ("q", "ㄆ"), ("w", "ㄊ"), ("e", "ㄍ"), ("r", "ㄐ"), ("t", "ㄔ"),
        ("y", "ㄗ"), ("u", "ㄧ"), ("i", "ㄛ"), ("o", "ㄟ"), ("p", "ㄣ"),
        # asdf row
        ("a", "ㄇ"), ("s", "ㄋ"), ("d", "ㄎ"), ("f", "ㄑ"), ("g", "ㄕ"),
        ("h", "ㄘ"), ("j", "ㄨ"), ("k", "ㄜ"), ("l", "ㄠ"), (";", "ㄤ"),
        # zxcv row
        ("z", "ㄈ"), ("x", "ㄌ"), ("c", "ㄏ"), ("v", "ㄒ"), ("b", "ㄖ"),
        ("n", "ㄙ"), ("m", "ㄩ"), (",", "ㄝ"), (".", "ㄡ"), ("/", "ㄥ"),
    ])
    def test_each_key(self, key, expected):
        assert DACHEN[key] == expected


# ============================================================
# 3. english_to_bopomofo() golden cases (from user's actual report)
# ============================================================

class TestEnglishToBopomofo:
    def test_jin_today(self):
        """rup → ㄐㄧㄣ (今, ㄐㄧㄣ tone-1 implicit)."""
        assert english_to_bopomofo("rup") == "ㄐㄧㄣ"

    def test_today_two_chars(self):
        """wu0 → ㄊㄧㄢ (天)."""
        assert english_to_bopomofo("wu0") == "ㄊㄧㄢ"

    def test_qi_with_tone4(self):
        """fu4 → ㄑㄧˋ (氣)."""
        assert english_to_bopomofo("fu4") == "ㄑㄧˋ"

    def test_zhen_implicit_tone1(self):
        """5p → ㄓㄣ (真) — first tone has no mark."""
        assert english_to_bopomofo("5p") == "ㄓㄣ"

    def test_hao_with_tone3(self):
        """cl3 → ㄏㄠˇ (好)."""
        assert english_to_bopomofo("cl3") == "ㄏㄠˇ"

    def test_full_user_example(self):
        """Whole 「今天天氣真好」 input."""
        assert english_to_bopomofo("rup wu0 wu0 fu4 5p cl3") == \
            "ㄐㄧㄣ ㄊㄧㄢ ㄊㄧㄢ ㄑㄧˋ ㄓㄣ ㄏㄠˇ"

    def test_toolskk_phrase(self):
        """vu04g;4ej/ rm4j;3 → 線上工 具網 (reference key sequence,
        though the homepage shows it as 線上工具網 — see note)."""
        assert english_to_bopomofo("vu04g;4ej/ rm4j;3") == \
            "ㄒㄧㄢˋㄕㄤˋㄍㄨㄥ ㄐㄩˋㄨㄤˇ"
        # Note: the actual toolskk homepage example was likely typed with
        # different syllable boundaries; layouts.py just does mechanical
        # English→Bopomofo, the IME engine handles syllable parsing later.

    def test_xian_shang_gong(self):
        """Verify each char's Bopomofo from libchewing's source."""
        assert english_to_bopomofo("vu04") == "ㄒㄧㄢˋ"  # 線
        assert english_to_bopomofo("g;4") == "ㄕㄤˋ"     # 上
        assert english_to_bopomofo("ej/") == "ㄍㄨㄥ"    # 工
        assert english_to_bopomofo("rm4") == "ㄐㄩˋ"     # 具
        assert english_to_bopomofo("j;3") == "ㄨㄤˇ"     # 網

    def test_uppercase_mapped_same_as_lowercase(self):
        """Bopomofo IME ignores Shift on letter keys."""
        assert english_to_bopomofo("RUP") == english_to_bopomofo("rup")

    def test_punctuation_and_cjk_pass_through(self):
        """! and CJK chars are not in the layout — must pass through unchanged."""
        # h=ㄘ e=ㄍ l=ㄠ l=ㄠ o=ㄟ → "ㄘㄍㄠㄠㄟ", and "!", " ", "你", "好" pass through.
        assert english_to_bopomofo("hello! 你好") == "ㄘㄍㄠㄠㄟ! 你好"

    def test_empty_input(self):
        assert english_to_bopomofo("") == ""

    def test_unknown_layout_raises(self):
        with pytest.raises(ValueError, match="unknown layout"):
            english_to_bopomofo("a", layout="russian")


# ============================================================
# 4. split_syllables()
# ============================================================

class TestSplitSyllables:
    def test_simple_with_tones(self):
        assert split_syllables("ㄑㄧˋㄏㄠˇ") == ["ㄑㄧˋ", "ㄏㄠˇ"]

    def test_implicit_tone_split_by_space(self):
        assert split_syllables("ㄐㄧㄣ ㄊㄧㄢ") == ["ㄐㄧㄣ", " ", "ㄊㄧㄢ"]

    def test_mixed_implicit_and_explicit(self):
        assert split_syllables("ㄐㄧㄣ ㄑㄧˋㄓㄣ ㄏㄠˇ") == \
            ["ㄐㄧㄣ", " ", "ㄑㄧˋ", "ㄓㄣ", " ", "ㄏㄠˇ"]

    def test_punctuation_kept_as_token(self):
        assert split_syllables("ㄏㄠˇ!") == ["ㄏㄠˇ", "!"]

    def test_empty(self):
        assert split_syllables("") == []
