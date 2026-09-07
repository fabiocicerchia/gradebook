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
    size = len(text)

    def blank(start: int, end: int) -> None:
        for index in range(max(start, 0), min(end, size)):
            if out[index] != "\n":
                out[index] = " "

    position = 0
    while position < size:
        char = text[position]
        token = next((t for t in line_tokens if text.startswith(t, position)), None)
        if token:
            end = text.find("\n", position)
            end = size if end == -1 else end
            blank(position, end)
            position = end
            continue
        pair = next((p for p in block_pairs if text.startswith(p[0], position)), None)
        if pair:
            end = text.find(pair[1], position + len(pair[0]))
            end = size if end == -1 else end + len(pair[1])
            blank(position, end)
            position = end
            continue
        if char in quotes:
            if triple and text.startswith(char * 3, position):
                end = text.find(char * 3, position + 3)
                end = size if end == -1 else end + 3
                blank(position + 3, end - 3)
                position = end
                continue
            cursor = position + 1
            while cursor < size:
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == char or text[cursor] == "\n":
                    break
                cursor += 1
            blank(position + 1, cursor)
            position = min(cursor + 1, size)
            continue
        position += 1
    return "".join(out)


