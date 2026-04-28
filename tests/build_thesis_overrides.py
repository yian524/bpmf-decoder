"""Build PREFERRED_CHAR overrides from actual thesis corpus.

Walk the user's 碩論 directory, count single-character frequencies in
real text. For each Bopomofo where multiple chars are valid, pick the
one most-frequent IN THE THESIS, not in pypinyin's phrase corpus.

Output: print Python dict literal that can be pasted into
chewing_wrapper.PREFERRED_CHAR.
"""
import sys
from collections import defaultdict
from pathlib import Path
import re

sys.path.insert(0, str(Path.home() / ".claude" / "scripts" / "bopo-fix"))
from pypinyin import Style, pinyin

CJK_RE = re.compile(r"[一-鿿]+")

def main():
    root = Path.home() / "Desktop" / "碩論"
    char_count = defaultdict(int)
    files_scanned = 0
    for p in root.rglob("*"):
        if files_scanned > 200:
            break
        if not p.is_file() or p.suffix.lower() not in {".md", ".txt", ".tex", ".jsx", ".py"}:
            continue
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if sz < 5_000 or sz > 5_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        files_scanned += 1
        for chunk in CJK_RE.findall(text):
            for ch in chunk:
                char_count[ch] += 1

    print(f"# scanned {files_scanned} files, {len(char_count)} unique chars, "
          f"{sum(char_count.values()):,} total CJK chars", file=sys.stderr)

    # For each Bopomofo, pick most-thesis-frequent char.
    bopo_to_best = {}  # bopo -> (char, count)
    for ch, cnt in char_count.items():
        try:
            result = pinyin(ch, style=Style.BOPOMOFO, errors="ignore")
        except Exception:
            continue
        if not result or not result[0] or not result[0][0]:
            continue
        bp = result[0][0]
        prev = bopo_to_best.get(bp)
        if prev is None or cnt > prev[1]:
            bopo_to_best[bp] = (ch, cnt)

    # Filter: only emit overrides for chars that appear ≥ 30 times in
    # the thesis (signal floor) — this gives us the "really used in
    # this user's writing" set, not random rare-char stuff.
    overrides = {bp: ch for bp, (ch, cnt) in bopo_to_best.items() if cnt >= 30}
    # Sort by Bopomofo for stable output.
    print("# Auto-generated thesis-corpus PREFERRED_CHAR (≥30 occurrences)", file=sys.stderr)
    print("THESIS_CORPUS_OVERRIDES = {")
    for bp in sorted(overrides):
        ch = overrides[bp]
        print(f'    {bp!r}: {ch!r},')
    print("}")
    print(f"# total entries: {len(overrides)}", file=sys.stderr)


if __name__ == "__main__":
    main()
