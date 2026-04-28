"""bopo_fix.py — entry point for the wrong-IME-layout undo tool.

Reads the garbled English-key text on stdin, prints the recovered
Traditional Chinese on stdout. Designed to be invoked by the
``bopo-fix.cmd`` shim which is itself called by AutoHotkey on hotkey
press.

CLI:

    echo rup wu0 wu0 fu4 5p cl3! | bopo-fix
    → 今天天氣真好！

Options:

    --layout {dachen}    Bopomofo keyboard layout (default: dachen)
    --no-punct           Skip ASCII→full-width punctuation conversion

The pipeline is intentionally tiny: layouts.english_to_bopomofo →
chewing_wrapper.bopomofo_to_traditional → punct.apply_chinese_punctuation.
Each step is independently testable in its own module.
"""
from __future__ import annotations

import argparse
import sys

from chewing_wrapper import bopomofo_to_traditional
from layouts import english_to_bopomofo
from punct import apply_chinese_punctuation


def _collapse_inter_cjk_spaces(text: str) -> str:
    """Drop runs of whitespace that sit between two CJK chars.

    The input English was typed with spaces between syllables (the user's
    natural typing rhythm), but in Chinese the spaces are not part of
    the sentence. We strip them when both sides are CJK; we keep them
    when at least one side is ASCII / digit (deliberate word boundary).
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            j = i
            while j < n and text[j].isspace():
                j += 1
            left = out[-1] if out else ""
            right = text[j] if j < n else ""
            if left and right and _is_cjk(left) and _is_cjk(right):
                # Drop the whitespace run.
                i = j
                continue
            out.append(text[i:j])
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# Bopomofo finals that double as ASCII punctuation in the Dachen layout.
# When these characters survive into the converter's output (because they
# couldn't be assembled into a complete syllable), it means the user
# typed them as sentence punctuation, not as part of a Chinese syllable.
# We revert them so punct.apply_chinese_punctuation can promote to 全形.
_STANDALONE_BOPO_TO_ASCII: dict[str, str] = {
    "ㄝ": ",",  # Dachen: , key
    "ㄡ": ".",  # Dachen: . key
}


def _revert_standalone_bopomofo_punct(text: str) -> str:
    """Replace unmatched standalone Bopomofo finals with their ASCII keys.

    Conservative — only ㄝ and ㄡ, since these are the two Bopomofo
    characters that share keys with sentence-ending ASCII punctuation
    (`,` and `.`). All other Bopomofo letters either have unique keys
    or share keys with ASCII characters that wouldn't be sentence punct.

    A bopomofo letter that survives into the output means the syllable
    couldn't be resolved — almost certainly because the user typed
    ASCII punct, not because they wanted ㄝ/ㄡ on its own (those are
    never valid as a one-character syllable).
    """
    return "".join(_STANDALONE_BOPO_TO_ASCII.get(ch, ch) for ch in text)


def _is_cjk(ch: str) -> bool:
    """True for CJK Unified Ideographs + CJK punctuation."""
    if not ch:
        return False
    code = ord(ch[-1])
    return (
        0x4E00 <= code <= 0x9FFF      # CJK Unified Ideographs
        or 0x3000 <= code <= 0x303F   # CJK Symbols and Punctuation
        or 0xFF00 <= code <= 0xFFEF   # Halfwidth and Fullwidth Forms
    )


def convert(garbled: str, layout: str = "dachen", apply_punct: bool = True) -> str:
    """End-to-end: garbled English-keys → 繁體中文 (with full-width punct)."""
    bopo = english_to_bopomofo(garbled, layout=layout)
    chinese = bopomofo_to_traditional(bopo)
    # Revert unmatched ㄝ/ㄡ back to , / . so they can become ，/。 in the
    # punct stage. Only affects characters that didn't form a valid syllable.
    chinese = _revert_standalone_bopomofo_punct(chinese)
    chinese = _collapse_inter_cjk_spaces(chinese)
    if apply_punct:
        chinese = apply_chinese_punctuation(chinese)
    return chinese


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="bopo-fix",
        description="Recover Traditional Chinese from English-keys typed with the wrong IME state.",
    )
    p.add_argument(
        "--layout",
        default="dachen",
        choices=["dachen", "standard"],
        help="Bopomofo keyboard layout (default: dachen, alias: standard)",
    )
    p.add_argument(
        "--no-punct",
        action="store_true",
        help="Skip ASCII → full-width punctuation conversion.",
    )
    p.add_argument(
        "--input-file",
        default=None,
        help="Read input text from this UTF-8 file instead of stdin / argv. "
             "Used by the AHK hotkey shim to avoid Windows shell-redirection "
             "pitfalls when the input contains punctuation that cmd.exe parses.",
    )
    p.add_argument(
        "--output-file",
        default=None,
        help="Write recovered Chinese to this UTF-8 file instead of stdout. "
             "Pairs with --input-file for AHK integration.",
    )
    p.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Input text. If omitted, reads from stdin (or --input-file).",
    )
    args = p.parse_args(argv)

    if args.input_file is not None:
        from pathlib import Path
        garbled = Path(args.input_file).read_text(encoding="utf-8")
    elif args.text is not None:
        garbled = args.text
    else:
        # Bytes → str via UTF-8 (Windows console default-cp may not be UTF-8;
        # AHK pipes raw clipboard bytes here — we trust the caller to
        # pre-encode).
        garbled = sys.stdin.read()

    out = convert(garbled, layout=args.layout, apply_punct=not args.no_punct)

    if args.output_file is not None:
        from pathlib import Path
        Path(args.output_file).write_text(out, encoding="utf-8")
    else:
        # Use sys.stdout.buffer to ensure UTF-8 output regardless of console
        # codepage (Windows default cp950 / cp1252 would mangle CJK).
        try:
            sys.stdout.buffer.write(out.encode("utf-8"))
            sys.stdout.buffer.flush()
        except AttributeError:
            # Fallback for environments without .buffer (rare; e.g., tests
            # capturing stdout via StringIO).
            sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
