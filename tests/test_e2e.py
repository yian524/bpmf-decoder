"""End-to-end tests: the user's reported scenario, through the full pipeline.

This is the test that proves the tool works for the canonical use case:

    "rup wu0 wu0 fu4 5p cl3!"   (wrong-IME English garble)
        ↓
    "今天天氣真好！"            (recovered Traditional Chinese)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest

from bopo_fix import convert


# ============================================================
# 1. The user's golden reproducer
# ============================================================

class TestUserGoldenScenario:
    """The user's literal problem statement."""

    def test_today_weather_is_good(self):
        """rup wu0 wu0 fu4 5p cl3! → 今天天氣真好！

        Spaces between syllables are inter-CJK and get collapsed by
        _collapse_inter_cjk_spaces in the pipeline.
        """
        assert convert("rup wu0 wu0 fu4 5p cl3!") == "今天天氣真好！"

    def test_xian_shang_gong_ju_wang(self):
        """vu04 g;4 ej/ rm4 j;3 → 線上工具網 (toolskk reference example)."""
        assert convert("vu04 g;4 ej/ rm4 j;3") == "線上工具網"


class TestSinglePhrases:
    @pytest.mark.parametrize("garbled,expected", [
        ("rup", "今"),
        ("wu0", "天"),
        ("fu4", "氣"),
        ("5p", "真"),
        ("cl3", "好"),
        ("vu04", "線"),
        ("g;4", "上"),
        ("ej/", "工"),
        ("rm4", "具"),
        ("j;3", "網"),
    ])
    def test_each(self, garbled, expected):
        assert convert(garbled) == expected


class TestPunctuation:
    def test_question_mark(self):
        # 你好嗎? = ㄋㄧˇㄏㄠˇㄇㄚ? → "j6cl3a8?" but key seq depends on
        # exact tones; let's just construct the Bopomofo path directly.
        # Use the convert() pipeline on a known clean Bopomofo path:
        # ㄋㄧˇㄏㄠˇ ㄇㄚ?
        # Mapping back: "ji3 cl3 ?? ..." — too convoluted. Just test ! and ?.
        assert convert("rup!") == "今！"
        assert convert("rup?") == "今？"


# ============================================================
# 2. CLI subprocess test (ensures stdout encoding works on Windows)
# ============================================================

class TestCliInvocation:
    """Verify the CLI binary is callable end-to-end as the AHK script will.

    Skipped if the venv python isn't where we expect — the test is
    machine-specific to the user's bopo-fix install layout.
    """

    @pytest.fixture
    def cli_python(self):
        py = Path.home() / ".claude" / "scripts" / "bopo-fix" / ".venv" / "Scripts" / "python.exe"
        if not py.exists():
            pytest.skip(f"venv python not found at {py}")
        return str(py)

    @pytest.fixture
    def cli_script(self):
        return str(Path.home() / ".claude" / "scripts" / "bopo-fix" / "bopo_fix.py")

    def test_stdin_pipeline(self, cli_python, cli_script):
        """Pipe input → bopo_fix.py → stdout, decode UTF-8."""
        proc = subprocess.run(
            [cli_python, cli_script],
            input="rup wu0 wu0 fu4 5p cl3!".encode("utf-8"),
            capture_output=True,
            timeout=20,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
        out = proc.stdout.decode("utf-8")
        assert out == "今天天氣真好！", f"got {out!r}"

    def test_arg_input(self, cli_python, cli_script):
        """Pass input as positional arg instead of stdin."""
        proc = subprocess.run(
            [cli_python, cli_script, "rup"],
            capture_output=True,
            timeout=20,
        )
        assert proc.returncode == 0
        out = proc.stdout.decode("utf-8")
        assert out == "今"
