"""Edge-case + robustness tests.

These cover the long tail of inputs the user might throw at the tool:
empty / whitespace-only, multi-line, mixed CJK + English garble, very
long inputs, CR/LF line endings, special punctuation. Goal is "graceful
behaviour or correct conversion — never a crash".
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest

from bopo_fix import _collapse_inter_cjk_spaces, _is_cjk, convert, main


# ============================================================
# Empty / whitespace-only inputs
# ============================================================

class TestEmptyInputs:
    def test_empty_string(self):
        assert convert("") == ""

    def test_only_spaces(self):
        # All whitespace, no syllables — should pass through (or collapse to nothing).
        result = convert("   ")
        assert result.strip() == ""

    def test_only_newlines(self):
        result = convert("\n\n")
        # Newlines between non-CJK should pass through.
        assert "\n" in result or result.strip() == ""

    def test_only_punctuation(self):
        # ASCII punctuation should be converted to full-width.
        # `,` and `.` are normally Bopomofo finals but the heuristic
        # in english_to_bopomofo treats them as ASCII punct when not
        # followed by a syllable-continuing character.
        assert convert("!?,.") == "！？，。"

    def test_sentence_ending_period(self):
        """rup wu0 wu0 fu4 5p cl3. → 今天天氣真好。 (period at EOF)."""
        assert convert("rup wu0 wu0 fu4 5p cl3.") == "今天天氣真好。"

    def test_sentence_ending_question_mark(self):
        assert convert("rup wu0 wu0 fu4 5p cl3?") == "今天天氣真好？"

    def test_comma_in_middle_of_sentence(self):
        """Comma followed by space → ASCII punct (not ㄝ)."""
        assert convert("你好,世界!") == "你好，世界！"

    def test_comma_inside_syllable(self):
        """`u,4` is a complete Bopomofo syllable for ㄧㄝˋ — the
        heuristic should preserve `,` as Bopomofo final (followed by
        digit `4`, mid-syllable). The chosen character is the highest-
        frequency Traditional one (葉 over 業 because 葉 appears in
        more phrases — both are valid surnames/words)."""
        result = convert("u,4")
        assert result in ("葉", "業"), f"got {result!r} — should be a valid ㄧㄝˋ char"

    def test_traditional_chinese_canonicalization(self):
        """Single chars whose pypinyin entry is Simplified must be
        promoted to Traditional via OpenCC s2twp at dict build time.
        No simplified forms should leak through."""
        result = convert("u,4 j;3 vu04")
        # No simplified forms allowed
        assert "业" not in result
        assert "网" not in result
        assert "线" not in result
        # Traditional forms (网→網, 线→線, ㄧㄝˋ → 葉/業 both valid)
        assert "網" in result
        assert "線" in result


# ============================================================
# Mixed input — CJK already present, English garble inserted
# ============================================================

class TestMixedContent:
    def test_cjk_passthrough(self):
        """Existing CJK chars must not be mangled."""
        # 這段沒有任何亂碼,只有CJK + ASCII punct.
        assert convert("你好,世界!") == "你好，世界！"

    def test_garble_then_cjk(self):
        """Wrong-IME garble followed by correct CJK."""
        # rup (今) followed by literal 天 (already correct CJK).
        assert convert("rup天") == "今天"

    def test_cjk_then_garble(self):
        """Correct CJK followed by wrong-IME garble."""
        assert convert("今wu0") == "今天"

    def test_multiple_garble_segments(self):
        """Multiple segments joined by punctuation."""
        # rup wu0 (今天) ! cl3 (好) — punct between segments.
        assert convert("rup wu0!cl3") == "今天！好"


# ============================================================
# Line endings + multi-line
# ============================================================

class TestLineEndings:
    def test_unix_newline(self):
        result = convert("rup\nwu0")
        # Newline should split CJK chars (each a separate logical line).
        assert "今" in result and "天" in result

    def test_windows_crlf(self):
        result = convert("rup\r\nwu0")
        assert "今" in result and "天" in result

    def test_multiple_lines(self):
        result = convert("rup\nwu0\nfu4")
        assert "今" in result and "天" in result and "氣" in result


# ============================================================
# Helper functions (direct unit tests for coverage)
# ============================================================

class TestIsCjk:
    @pytest.mark.parametrize("ch,expected", [
        ("你", True),  # CJK Unified
        ("好", True),
        ("。", True),  # CJK punctuation
        ("！", True),  # full-width
        ("a", False),
        ("1", False),
        (" ", False),
        ("!", False),  # ASCII punct
        ("", False),
    ])
    def test_classification(self, ch, expected):
        assert _is_cjk(ch) is expected


class TestCollapseInterCjkSpaces:
    def test_single_space_between_cjk(self):
        assert _collapse_inter_cjk_spaces("今 天") == "今天"

    def test_multiple_spaces_collapsed(self):
        assert _collapse_inter_cjk_spaces("今   天") == "今天"

    def test_space_kept_around_ascii(self):
        assert _collapse_inter_cjk_spaces("今 abc 天") == "今 abc 天"

    def test_no_change_when_no_inter_cjk_space(self):
        assert _collapse_inter_cjk_spaces("hello world") == "hello world"

    def test_empty(self):
        assert _collapse_inter_cjk_spaces("") == ""


# ============================================================
# CLI main() — argparse paths
# ============================================================

class TestCliMain:
    def test_text_arg(self, capsysbinary):
        rc = main(["rup wu0 wu0 fu4 5p cl3!"])
        assert rc == 0
        captured = capsysbinary.readouterr()
        assert captured.out.decode("utf-8") == "今天天氣真好！"

    def test_no_punct_flag(self, capsysbinary):
        rc = main(["--no-punct", "rup!"])
        assert rc == 0
        out = capsysbinary.readouterr().out.decode("utf-8")
        # ! should remain ASCII (not converted to ！)
        assert out == "今!"

    def test_layout_alias(self, capsysbinary):
        rc = main(["--layout", "standard", "rup"])
        assert rc == 0
        assert capsysbinary.readouterr().out.decode("utf-8") == "今"

    def test_stdin_when_no_arg(self, monkeypatch, capsysbinary):
        monkeypatch.setattr("sys.stdin", io.StringIO("rup"))
        rc = main([])
        assert rc == 0
        assert capsysbinary.readouterr().out.decode("utf-8") == "今"


# ============================================================
# Stress / volume
# ============================================================

class TestStress:
    def test_long_input(self):
        """500-char garble shouldn't crash or hang."""
        garble = "rup wu0 wu0 fu4 5p cl3! " * 50  # ~1200 chars
        result = convert(garble)
        # Should contain many copies of 今天天氣真好.
        assert result.count("今天天氣真好") >= 40

    def test_repeated_unknown_syllables(self):
        """Bopomofo that doesn't map to any character should pass through, not crash."""
        # ㄅ alone is a partial syllable.
        result = convert("1")  # → ㄅ alone
        # Either passes through ㄅ or drops it; just make sure it's stable.
        assert isinstance(result, str)

    def test_idempotent_on_chinese(self):
        """Running convert() on already-converted Chinese should be a no-op
        (since CJK chars aren't in DACHEN dict and pass through unchanged)."""
        once = convert("今天天氣真好！")
        twice = convert(once)
        assert once == twice == "今天天氣真好！"


# ============================================================
# Unicode safety
# ============================================================

class TestUnicodeSafety:
    def test_emoji_passthrough(self):
        assert "😀" in convert("rup😀wu0")

    def test_full_width_digits(self):
        # ＡＢＣ１２３ are full-width ASCII; not in DACHEN, pass through.
        assert convert("ＡＢＣ") == "ＡＢＣ"

    def test_zero_width_nonjoiner(self):
        zwnj = "‌"
        result = convert(f"rup{zwnj}wu0")
        # ZWNJ shouldn't affect logic; both syllables convert.
        assert "今" in result and "天" in result
