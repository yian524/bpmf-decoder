"""Unit tests for punct.apply_chinese_punctuation."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest

from punct import apply_chinese_punctuation


@pytest.mark.parametrize("ascii_,full", [
    ("!", "！"),
    ("?", "？"),
    (",", "，"),
    (".", "。"),
    (";", "；"),
    (":", "："),
])
def test_each_punct(ascii_, full):
    assert apply_chinese_punctuation(ascii_) == full


def test_chinese_chars_pass_through():
    assert apply_chinese_punctuation("今天") == "今天"


def test_mixed_sentence():
    assert apply_chinese_punctuation("今天天氣真好!") == "今天天氣真好！"
    assert apply_chinese_punctuation("你好嗎?我很好.") == "你好嗎？我很好。"


def test_idempotent():
    """Running twice doesn't double-convert."""
    once = apply_chinese_punctuation("今天天氣真好!")
    twice = apply_chinese_punctuation(once)
    assert once == twice == "今天天氣真好！"


def test_quotes_left_alone():
    """v1 doesn't touch quotes (ambiguous open vs close)."""
    assert apply_chinese_punctuation('"你好"') == '"你好"'
    assert apply_chinese_punctuation("'a'") == "'a'"


def test_letters_digits_unchanged():
    assert apply_chinese_punctuation("abc123") == "abc123"
