"""Build the English word list the router uses to tell a typing slip from a real word.

    python3 tools/build_lexicon.py [OUT]   (default: harness/app/routing/words.txt)

Sources are general English text on an Ubuntu install, nothing from a benchmark: package
documentation (/usr/share/doc), manual pages (/usr/share/man), the common licences and the
Python standard library's comments and docstrings. A lowercase word of 4 to 22 letters that
appears at least MIN_COUNT times is kept; a three-letter word needs MIN_COUNT_SHORT, since
documentation is full of three-letter abbreviations (tun, tel) that are not words a person
types.
"""
from __future__ import annotations

import collections
import gzip
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [Path("/usr/share/doc"), Path("/usr/share/man"), Path("/usr/share/common-licenses"), Path("/usr/lib/python3.12")]
WORD = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]{3,22}(?![A-Za-z0-9_])")
MIN_COUNT = 3
MIN_COUNT_SHORT = 300
MAX_FILE_BYTES = 4_000_000


def text_of(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        raw = gzip.open(path).read() if path.suffix == ".gz" else path.read_bytes()
    except (OSError, EOFError, gzip.BadGzipFile):
        return ""
    if b"\0" in raw[:4096]:
        return ""
    return raw.decode("utf-8", "ignore")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "harness" / "app" / "routing" / "words.txt"
    counts: collections.Counter[str] = collections.Counter()
    files = 0
    for source in SOURCES:
        for path in source.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            text = text_of(path)
            if not text:
                continue
            files += 1
            # Only all-lowercase or capitalised words: camelCase and ALLCAPS are identifiers, not English.
            counts.update(word.lower() for word in WORD.findall(text) if word.islower() or (word[0].isupper() and word[1:].islower()))
    words = sorted(word for word, count in counts.items() if count >= (MIN_COUNT_SHORT if len(word) == 3 else MIN_COUNT))
    out.write_text("\n".join(words) + "\n", encoding="utf-8")
    print(f"{len(words)} words from {files} files -> {out}")


if __name__ == "__main__":
    main()
