"""Tests for chewing_wrapper.bopomofo_to_traditional.

Heavy-ish tests because the engine builds 41k-entry CJK reverse dict.
We use a session-scoped fixture so the dict is built once across all
tests in this module (~1.5s up front vs per-test).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest

from chewing_wrapper import bopomofo_to_traditional


@pytest.fixture(scope="module", autouse=True)
def warm_dict():
    """Force the reverse dict to build before any test runs (so timing of
    individual tests reflects only conversion cost, not dict construction).
    """
    t0 = time.monotonic()
    bopomofo_to_traditional("ㄐㄧㄣ")  # any call warms the lru_cache
    print(f"\n[chewing_wrapper] reverse dict built in {time.monotonic()-t0:.2f}s")


# ============================================================
# Core golden cases — the user's reported scenario
# ============================================================

class TestUserGoldenCase:
    """The whole-sentence 「今天天氣真好」 round-trip."""

    def test_jin_today(self):
        assert bopomofo_to_traditional("ㄐㄧㄣ") == "今"

    def test_tian_day(self):
        assert bopomofo_to_traditional("ㄊㄧㄢ") == "天"

    def test_qi_air(self):
        assert bopomofo_to_traditional("ㄑㄧˋ") == "氣"

    def test_zhen_real(self):
        assert bopomofo_to_traditional("ㄓㄣ") == "真"

    def test_hao_good(self):
        assert bopomofo_to_traditional("ㄏㄠˇ") == "好"

    def test_full_sentence_with_spaces(self):
        """Each syllable separated by space (tone-1 implicit)."""
        result = bopomofo_to_traditional(
            "ㄐㄧㄣ ㄊㄧㄢ ㄊㄧㄢ ㄑㄧˋ ㄓㄣ ㄏㄠˇ"
        )
        # Spaces should be preserved (caller decides whether to strip).
        # Char output is the priority.
        cleaned = result.replace(" ", "")
        assert cleaned == "今天天氣真好", \
            f"expected 今天天氣真好, got {cleaned!r} (raw={result!r})"


class TestSingleCharsFromPreferredTable:
    """Spot-check that PREFERRED_CHAR overrides resolve correctly."""

    @pytest.mark.parametrize("bopo,char", [
        ("ㄉㄜ˙", "的"),
        ("ㄕˋ", "是"),
        ("ㄅㄨˋ", "不"),
        ("ㄨㄛˇ", "我"),
        ("ㄋㄧˇ", "你"),
        ("ㄕㄤˋ", "上"),
        ("ㄍㄨㄥ", "工"),
        ("ㄐㄩˋ", "具"),
        ("ㄨㄤˇ", "網"),
        ("ㄒㄧㄢˋ", "線"),
    ])
    def test_preferred(self, bopo, char):
        assert bopomofo_to_traditional(bopo) == char


class TestUnknownPassthrough:
    """Bopomofo not in any dict comes through as-is so the user can debug."""

    def test_punctuation(self):
        assert bopomofo_to_traditional("!") == "!"
        assert bopomofo_to_traditional("?") == "?"

    def test_mixed_unknown_and_known(self):
        # Cross-space phrase matching now collapses syllable-boundary
        # whitespace so "ㄐㄧㄣ ㄊㄧㄢ" can match the phrase 今天 in
        # phrase_dict (improvement over the previous "今 天" output).
        assert bopomofo_to_traditional("ㄐㄧㄣ ㄊㄧㄢ!") == "今天!"


class TestPhrasesGreedyMatch:
    """Multi-syllable matches against phrases_dict reversed."""

    def test_now_phrase(self):
        # 現在 = ㄒㄧㄢˋㄗㄞˋ — should hit the manual override 現在
        assert bopomofo_to_traditional("ㄒㄧㄢˋㄗㄞˋ") == "現在"

    def test_what_phrase(self):
        # 什麼 = ㄕㄣˊㄇㄜ˙
        assert bopomofo_to_traditional("ㄕㄣˊㄇㄜ˙") == "什麼"


# ============================================================
# Smoke / property tests
# ============================================================

class TestEmpty:
    def test_empty_string(self):
        assert bopomofo_to_traditional("") == ""

    def test_only_whitespace(self):
        assert bopomofo_to_traditional("   ") == "   "
