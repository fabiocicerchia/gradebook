from pathlib import Path

d = Path(__file__).parent / "gradebook-tests" / "gradebook_tests"
src = (d / "detection.py").read_text().splitlines(keepends=True)


def L(a, b):
    return "".join(src[a - 1 : b])


pat_blocks = [L(74, 518), L(552, 612), L(626, 668), L(701, 836), L(901, 910)]
patterns = (
    '"""The patterns that recognise what is inside a test file: case and\n'
    "assertion syntax per language, smells, doubles, and the word lists that\n"
    'judge a test name. Data only — the code that applies them is in detection."""\n\n'
    "import re\n\n" + "".join(pat_blocks)
).rstrip("\n") + "\n"
walking = (
    '"""Reading the working tree: the walk and the file reads, the only I/O\n'
    'the detectors need."""\n\nfrom __future__ import annotations\n\nimport os\n'
    "from collections.abc import Iterator\nfrom pathlib import Path\n\n"
    "from .base import ARTIFACT_DIRS, LANG_BY_EXT, MAX_FILE_BYTES, SKIP_DIRS\n\n"
    "# ------------------------------------------------------------------ walking\n\n\n" + L(875, 899)
).rstrip("\n") + "\n"
(d / "patterns.py").write_text(patterns)
(d / "walking.py").write_text(walking)
(d / "detection.py").write_text(
    L(1, 73) + L(520, 551) + L(613, 625) + L(669, 700) + L(837, 871) + L(911, len(src))
)
