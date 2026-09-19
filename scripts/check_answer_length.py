"""Check each application answer against the 200-word limit.

The form counts words, not characters, and silently truncates. Run this before
pasting anything in.

Usage: python scripts/check_answer_length.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LIMIT = 200
DOC = Path(__file__).resolve().parents[1] / "docs" / "application-answers.md"


def word_count(text: str) -> int:
    """Count words the way a web form would.

    Placeholders in [[double brackets]] are instructions to ourselves, not part
    of the answer, so they are excluded.
    """
    text = re.sub(r"\[\[.*?\]\]", " ", text, flags=re.S)
    return len(text.split())


def main() -> int:
    if not DOC.exists():
        print(f"missing {DOC}")
        return 1

    body = DOC.read_text(encoding="utf-8")
    sections = re.split(r"^## (Q\d\..*)$", body, flags=re.M)[1:]

    failures = 0
    for heading, text in zip(sections[0::2], sections[1::2]):
        text = text.split("\n---", 1)[0]
        n = word_count(text)
        status = "OK  " if n <= LIMIT else "OVER"
        if n > LIMIT:
            failures += 1
        label = heading.split(".")[0]
        print(f"  {status}  {label}: {n:3d} / {LIMIT} words"
              + (f"   ({n - LIMIT} over)" if n > LIMIT else ""))

    print()
    if failures:
        print(f"{failures} answer(s) over the limit — trim before submitting.")
        return 1
    print("all answers within the limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
