"""Unit tests for the small pure helpers: severity buckets and noise stripping."""

import pytest

from gradebook_code import FLAG_ORDER, severity_for, strip_noise

# ---------------------------------------------------------------- severity


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("hotspot", "high"),
        ("dependency-cycle", "high"),
        ("god-file", "high"),
        ("complex-function", "high"),
        ("duplicate-block", "medium"),
        ("fat-interface", "medium"),
        ("dead-code", "low"),
        ("many-parameters", "low"),
    ],
)
def test_severity_buckets_follow_flag_order(kind, expected):
    assert severity_for(kind) == expected


def test_unknown_kinds_are_low_severity():
    assert severity_for("no-such-detector") == "low"


def test_severity_never_rises_as_rank_falls():
    order = ["high", "medium", "low"]
    ranked = sorted(FLAG_ORDER, key=FLAG_ORDER.get)
    levels = [order.index(severity_for(kind)) for kind in ranked]
    assert levels == sorted(levels)


# ------------------------------------------------------------- strip_noise


def blanked(source, lang):
    stripped = strip_noise(source, lang)
    assert len(stripped) == len(source)
    assert stripped.count("\n") == source.count("\n")
    return stripped


def test_block_comments_are_blanked_across_lines():
    stripped = blanked("a = 1; /* if\nwhile */ b = 2;\n", "javascript")
    assert "if" not in stripped
    assert "while" not in stripped
    assert "a = 1;" in stripped
    assert "b = 2;" in stripped


def test_lua_and_ruby_use_their_own_comment_markers():
    assert "secret" not in blanked("x = 1 -- secret\n", "lua")
    assert "secret" not in blanked("=begin\nsecret\n=end\nx = 1\n", "ruby")


def test_slashes_are_code_where_hash_is_the_comment():
    stripped = blanked("x = 4 // 2  # note\n", "python")
    assert "//" in stripped
    assert "note" not in stripped


def test_triple_quoted_strings_keep_their_delimiters():
    stripped = blanked('x = """if\nfor"""\n', "python")
    assert stripped.startswith('x = """')
    assert "if" not in stripped
    assert "for" not in stripped
    assert stripped.rstrip().endswith('"""')


def test_escaped_quotes_do_not_end_the_string():
    stripped = blanked('s = "a\\"if"; t = 1;\n', "javascript")
    assert "if" not in stripped
    assert "t = 1;" in stripped


def test_backticks_are_strings_only_where_the_language_says_so():
    assert "if" not in blanked("s = `if`;\n", "go")
    assert "`if`" in blanked("s = `if`\n", "python")


def test_an_unterminated_string_stops_at_the_end_of_the_line():
    stripped = blanked('s = "open\nif x:\n', "python")
    assert "open" not in stripped
    assert "if x:" in stripped


def test_unterminated_block_comment_runs_to_the_end():
    stripped = blanked("x = 1; /* if\nwhile", "c")
    assert stripped.startswith("x = 1;")
    assert stripped[7:].strip() == ""
