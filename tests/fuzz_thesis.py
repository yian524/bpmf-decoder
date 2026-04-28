"""Fuzz test against any Chinese-text corpus.

Round-trip pipeline:
   Chinese → pypinyin Bopomofo → reverse-layout English keys
           → bopo-fix CLI → 還原中文
   compare(original, recovered)

Sources random Chinese snippets from a directory of .md/.txt files.
Reports per-char accuracy and lists characters that consistently get
mistranslated so you can target them in PREFERRED_CHAR or expand
CC-CEDICT phrase coverage.

Usage:
    python tests/fuzz_thesis.py --root ~/my-text-folder --samples 100
    python tests/fuzz_thesis.py --root /path/to/corpus --min 20 --max 150
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pypinyin import Style, pinyin

from bopo_fix import convert
from layouts import DACHEN

# Reverse-direction layout: Bopomofo symbol → English key.
# Built by inverting layouts.DACHEN.
_BOPO_TO_KEY: dict[str, str] = {bp: k for k, bp in DACHEN.items()}


def bopomofo_to_keys(bopo: str) -> str:
    """Convert a Bopomofo syllable string back to the English key sequence
    a user would type. E.g. 'ㄐㄧㄣ' → 'rup', 'ㄑㄧˋ' → 'fu4'."""
    out: list[str] = []
    for ch in bopo:
        key = _BOPO_TO_KEY.get(ch)
        if key is None:
            # Non-Bopomofo char (punct etc.) — pass through.
            out.append(ch)
        else:
            out.append(key)
    return "".join(out)


_CJK_RE = re.compile(r"[一-鿿]")
_CJK_CHUNK_RE = re.compile(r"[一-鿿]+")


def collect_thesis_snippets(root: Path, min_len: int, max_len: int,
                             samples: int) -> list[str]:
    """Walk the thesis directory, find files with substantial Chinese
    content, randomly extract `samples` snippets of length min..max chars
    (Chinese chars only — excludes punct/digits/Latin)."""
    candidates: list[str] = []
    seen_files = 0
    text_exts = {".md", ".txt", ".tex", ".jsx", ".py"}
    for path in root.rglob("*"):
        if seen_files > 200:
            break
        if not path.is_file():
            continue
        if path.suffix.lower() not in text_exts:
            continue
        try:
            sz = path.stat().st_size
        except OSError:
            continue
        if sz < 5_000 or sz > 5_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        seen_files += 1
        # Pull all CJK chunks of length >= min_len.
        for m in _CJK_CHUNK_RE.finditer(text):
            chunk = m.group(0)
            if len(chunk) >= min_len:
                candidates.append(chunk)

    if not candidates:
        return []

    random.shuffle(candidates)
    out: list[str] = []
    for c in candidates:
        if len(out) >= samples:
            break
        # Pick a random sub-slice within [min_len, min(max_len, len(c))].
        upper = min(max_len, len(c))
        if upper < min_len:
            continue
        slice_len = random.randint(min_len, upper)
        if slice_len >= len(c):
            out.append(c)
        else:
            start = random.randint(0, len(c) - slice_len)
            out.append(c[start:start + slice_len])
    return out


def round_trip(original: str) -> tuple[str, str]:
    """Forward Chinese → Bopomofo → keys, then bopo-fix back to Chinese.
    Returns (english_keys, recovered_chinese)."""
    # Forward: Chinese → Bopomofo (one syllable per char).
    bopo_per_char = pinyin(original, style=Style.BOPOMOFO, errors="ignore")
    # Concatenate with spaces between syllables (mimics how user types).
    bopo_str = " ".join(p[0] for p in bopo_per_char if p)
    # Reverse layout: Bopomofo → English keys.
    keys = bopomofo_to_keys(bopo_str)
    # Now run through bopo-fix (the actual production code path).
    recovered = convert(keys)
    return keys, recovered


def char_diff(original: str, recovered: str) -> list[tuple[int, str, str]]:
    """Naive char-by-char diff, ignoring whitespace differences.
    Returns list of (position, expected_char, got_char) for mismatches."""
    a = original
    b = "".join(ch for ch in recovered if not ch.isspace())
    diffs: list[tuple[int, str, str]] = []
    for i, ch_a in enumerate(a):
        ch_b = b[i] if i < len(b) else ""
        if ch_a != ch_b:
            diffs.append((i, ch_a, ch_b))
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True,
                    help="Directory of .md/.txt files to sample from.")
    ap.add_argument("--samples", type=int, default=30)
    ap.add_argument("--min", type=int, default=20)
    ap.add_argument("--max", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    random.seed(args.seed)
    root = Path(args.root)
    if not root.exists():
        print(f"❌ root not found: {root}", file=sys.stderr)
        return 2

    print(f"📚 sampling from {root} (size {args.min}-{args.max} chars × "
          f"{args.samples} cases)…")
    snippets = collect_thesis_snippets(root, args.min, args.max, args.samples)
    if not snippets:
        print("❌ no snippets found")
        return 2
    print(f"   → got {len(snippets)} snippets")

    total_chars = 0
    total_correct = 0
    error_chars = Counter()        # char user typed → counted error
    confused_pairs = Counter()      # (expected, got) pair frequency
    failure_examples: list[dict] = []

    for i, original in enumerate(snippets, 1):
        keys, recovered = round_trip(original)
        diffs = char_diff(original, recovered)
        n = len(original)
        total_chars += n
        total_correct += n - len(diffs)
        for _, exp, got in diffs:
            if exp != got:
                error_chars[exp] += 1
                confused_pairs[(exp, got)] += 1
        if diffs:
            failure_examples.append({
                "case": i,
                "original": original,
                "keys": keys,
                "recovered": recovered,
                "n_diffs": len(diffs),
                "diffs": [(p, e, g) for p, e, g in diffs[:10]],
            })

    accuracy = total_correct / total_chars if total_chars else 0
    print()
    print(f"✅ correct chars: {total_correct} / {total_chars} ({accuracy:.1%})")
    print(f"❌ failed cases: {len(failure_examples)} / {len(snippets)}")
    print()

    if confused_pairs:
        print("📋 Top confused pairs (expected → got, with count):")
        for (exp, got), n in confused_pairs.most_common(30):
            print(f"   {exp} → {got!s:>2}  × {n}")

    if failure_examples and len(failure_examples) <= 20:
        print()
        print("🔍 Failure examples:")
        for ex in failure_examples[:10]:
            print(f"   #{ex['case']} ({ex['n_diffs']} errs):")
            print(f"      orig:  {ex['original']}")
            print(f"      recov: {ex['recovered']}")
            print(f"      diffs: {ex['diffs']}")

    if args.report:
        Path(args.report).write_text(
            json.dumps(
                {
                    "accuracy": accuracy,
                    "total_chars": total_chars,
                    "total_correct": total_correct,
                    "n_failed_cases": len(failure_examples),
                    "n_total_cases": len(snippets),
                    "confused_pairs": [
                        {"expected": e, "got": g, "count": n}
                        for (e, g), n in confused_pairs.most_common(100)
                    ],
                    "failure_examples": failure_examples[:30],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\n📁 report saved: {args.report}")

    # Exit non-zero if accuracy is poor (< 90%) so this can gate CI.
    return 0 if accuracy >= 0.90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
