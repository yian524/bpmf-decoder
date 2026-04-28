"""build_thesis_phrases.py — regenerate thesis_phrase_overrides.py from corpus.

Walks the user's 碩論 directory, mines 2-4 char phrases that appear
≥ 30 times, and writes a Python dict literal mapping their Bopomofo
to the phrase text. The output replaces ../thesis_phrase_overrides.py.

Usage:
    python tests/build_thesis_phrases.py
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from chewing_wrapper import _bopomofo_of_phrase

CJK = re.compile(r"[一-鿿]+")
THRESHOLD = 30
MAX_PHRASES = 500
ROOT = Path.home() / "Desktop" / "碩論"
OUTFILE = _HERE / "thesis_phrase_overrides.py"


def main() -> int:
    if not ROOT.exists():
        print(f"❌ corpus root not found: {ROOT}", file=sys.stderr)
        return 2

    phrase_count: Counter[str] = Counter()
    files = 0
    for p in ROOT.rglob("*"):
        if files > 50:
            break
        if not p.is_file() or p.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if sz < 5_000 or sz > 1_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        files += 1
        for chunk in CJK.findall(text):
            for size in (2, 3, 4):
                for i in range(len(chunk) - size + 1):
                    phrase_count[chunk[i:i + size]] += 1

    common = [(p, c) for p, c in phrase_count.most_common(2000)
              if c >= THRESHOLD]
    print(f"# scanned {files} files, {len(common)} phrases ≥ {THRESHOLD} occurrences",
          file=sys.stderr)

    lines = [
        '"""thesis_phrase_overrides.py — auto-generated phrase preferences.',
        "",
        "Mined from user's 碩論 directory (top 500 phrases of length 2-4 that",
        f"appear ≥ {THRESHOLD} times).",
        "",
        "Re-generate with: python tests/build_thesis_phrases.py",
        '"""',
        "from __future__ import annotations",
        "",
        "THESIS_PHRASES = {",
    ]
    for phrase, count in common[:MAX_PHRASES]:
        bopo = _bopomofo_of_phrase(phrase)
        if bopo:
            lines.append(f"    {bopo!r}: {phrase!r},  # {count}")
    lines.append("}")
    OUTFILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ wrote {OUTFILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
