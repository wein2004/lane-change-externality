"""Enforce the deck's copy rules against scripts/slides_content.py.

Two house rules, both easy to break by accident when editing copy:

  1. Slide titles carry no punctuation.
  2. No contrastive "not X but Y" constructions anywhere in the deck.

Run: python scripts/check_slide_copy.py
Exits non-zero on any violation, so CI fails rather than shipping the deck.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from slides_content import DECK  # noqa: E402

TITLE_PUNCTUATION = "。，、：；？！「」『』（）《》〈〉—…·,.:;?!"

# The construction the deck avoids, plus its near relatives. "是不是" is
# excluded deliberately: it is a question form, not the contrastive pattern.
BANNED_PHRASES = ["不是", "而是", "而非", "並非", "與其", "不僅"]
ALLOWED_SUBSTRINGS = ["是不是", "是否"]


def walk(obj, path: str):
    """Yield every (path, string) in a nested structure."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            yield from walk(value, f"{path}[{i}]")


def main() -> int:
    failures: list[str] = []

    for i, slide in enumerate(DECK, start=1):
        label = f"p{i:02d} {slide.get('title', slide['layout'])}"

        title = slide.get("title", "")
        found = sorted({ch for ch in title if ch in TITLE_PUNCTUATION})
        if found:
            failures.append(
                f"{label}: 標題含標點 {found} — 改用空格分隔"
            )

        for path, text in walk(slide, ""):
            cleaned = text
            for allowed in ALLOWED_SUBSTRINGS:
                cleaned = cleaned.replace(allowed, "")
            for phrase in BANNED_PHRASES:
                if phrase in cleaned:
                    snippet = text.strip()[:60]
                    failures.append(
                        f"{label}{path}: 對比句型「{phrase}」— {snippet}"
                    )
                    break

    print(f"檢查 {len(DECK)} 頁投影片文案")
    if failures:
        print(f"\n{len(failures)} 項違規：")
        for line in failures:
            print(f"  {line}")
        return 1
    print("  標題無標點符號")
    print("  無對比句型")
    return 0


if __name__ == "__main__":
    sys.exit(main())
