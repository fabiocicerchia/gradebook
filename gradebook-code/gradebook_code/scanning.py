"""Walking the tree and reading files safely."""

from __future__ import annotations

# --------------------------------------------------------------- scanning

# Every metric below counts keywords, braces and dots. Counting the ones that
# live inside comments and string literals is the single largest source of
# error in a regex-based reader: a docstring that says "if the kind is a
# circle, for squares, while you are at it" adds four branches to a function
# that has none. Blanking them first is what makes the numbers mean anything —
# and it works the same way for every language rather than only where a parser
# happens to be available.
LINE_COMMENTS = {
    "python": ("#",),
    "ruby": ("#",),
    "shell": ("#",),
    "elixir": ("#",),
    "lua": ("--",),
    "php": ("//", "#"),
    "sql": ("--",),
}
BLOCK_COMMENTS = {
    "lua": (("--[[", "]]"),),
    "ruby": (("=begin", "=end"),),
    "python": (),
    "shell": (),
    "elixir": (),
}
STRING_QUOTES = {
    "go": ('"', "'", "`"),
    "javascript": ('"', "'", "`"),
    "typescript": ('"', "'", "`"),
    "scala": ('"',),
    "elixir": ('"', "'"),
    "shell": ('"', "'"),
}
TRIPLE_QUOTE_LANGS = {"python", "scala", "elixir", "kotlin"}
DEFAULT_LINE_COMMENTS = ("//",)
DEFAULT_BLOCK_COMMENTS = (("/*", "*/"),)
DEFAULT_QUOTES = ('"', "'")


def _blank(out: list[str], start: int, end: int) -> None:
    for index in range(max(start, 0), min(end, len(out))):
        if out[index] != "\n":
            out[index] = " "


def _comment_end(text: str, position: int, line_tokens: tuple, block_pairs: tuple) -> int | None:
    """Where the comment opening at `position` ends, or None if none opens there."""
    if any(text.startswith(token, position) for token in line_tokens):
        end = text.find("\n", position)
        return len(text) if end == -1 else end
    pair = next((p for p in block_pairs if text.startswith(p[0], position)), None)
    if pair:
        end = text.find(pair[1], position + len(pair[0]))
        return len(text) if end == -1 else end + len(pair[1])
    return None


def _string_span(text: str, position: int, triple: bool) -> tuple[int, int, int]:
    """The contents to blank, and where to resume, for the string opening at `position`."""
    char = text[position]
    size = len(text)
    if triple and text.startswith(char * 3, position):
        end = text.find(char * 3, position + 3)
        end = size if end == -1 else end + 3
        return position + 3, end - 3, end
    cursor = position + 1
    while cursor < size and text[cursor] not in (char, "\n"):
        cursor += 2 if text[cursor] == "\\" else 1
    return position + 1, cursor, min(cursor + 1, size)


def strip_noise(text: str, lang: str) -> str:
    """Blank comments and string contents, preserving length and line numbers.

    Offsets are unchanged, so every line number reported against the result is
    still correct against the original file.
    """
    line_tokens = LINE_COMMENTS.get(lang, DEFAULT_LINE_COMMENTS)
    block_pairs = BLOCK_COMMENTS.get(lang, DEFAULT_BLOCK_COMMENTS)
    quotes = STRING_QUOTES.get(lang, DEFAULT_QUOTES)
    triple = lang in TRIPLE_QUOTE_LANGS
    out = list(text)
    position = 0
    while position < len(text):
        end = _comment_end(text, position, line_tokens, block_pairs)
        if end is not None:
            _blank(out, position, end)
            position = end
        elif text[position] in quotes:
            start, stop, position = _string_span(text, position, triple)
            _blank(out, start, stop)
        else:
            position += 1
    return "".join(out)
