"""Check each application answer against the 200-word limit.

Only the English block under "## 英文" is counted — that is what gets pasted
into the form. The Chinese block below it is a reading aid and is ignored.

The form counts words, not characters, and truncates silently. Run this before
pasting anything in.

Usage: python scripts/check_answer_length.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LIMIT = 200
DOC = Path(__file__).resolve().parents[1] / "docs" / "application-answers.md"

# Start of a question block, and the English sub-block inside it.
QUESTION = re.compile(r"^# (Q\d)\s*$", re.M)
ENGLISH = re.compile(r"^## 英文.*?$(.*?)(?=^## |\Z)", re.M | re.S)


def word_count(text: str) -> int:
    return len(text.split())


def main() -> int:
    if not DOC.exists():
        print(f"missing {DOC}")
        return 1

    body = DOC.read_text(encoding="utf-8")
    parts = QUESTION.split(body)[1:]
    if not parts:
        print("FAIL: no question blocks found — has the document structure changed?")
        return 1

    failures = 0
    checked = 0
    for label, block in zip(parts[0::2], parts[1::2]):
        match = ENGLISH.search(block)
        if match is None:
            print(f"  FAIL  {label}: no '## 英文' block found")
            failures += 1
            continue
        n = word_count(match.group(1))
        checked += 1
        over = n > LIMIT
        failures += over
        print(f"  {'OVER' if over else 'OK  '}  {label}: {n:3d} / {LIMIT} words"
              + (f"   ({n - LIMIT} over)" if over else ""))

    print()
    if checked != 3:
        print(f"FAIL: expected 3 answers, found {checked}")
        return 1
    if failures:
        print(f"{failures} answer(s) over the limit — trim before submitting.")
        return 1
    print("all 3 answers within the limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
