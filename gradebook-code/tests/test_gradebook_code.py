import ast
import json
import subprocess
from pathlib import Path

import pytest

from gradebook_code import (
    DEFAULT_PROFILE,
    analyse_file,
    blend_profile,
    body_of,
    collect,
    count_params,
    evaluate,
    find_cycles,
    find_duplicate_blocks,
    find_hotspots,
    git_churn,
    is_generated,
    is_test_file,
    main,
    nesting_depth,
    recommendations,
    render_markdown,
    render_text,
    score_directories,
    strip_noise,
)


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def report_for(root):
    return evaluate(collect(root))


def dim(report, key):
    return next(d for d in report["dimensions"] if d["id"] == key)


def findings_of(report, kind):
    return [f for f in report["findings"] if f["kind"] == kind]


PROFILE = {
    "max_lines": DEFAULT_PROFILE[0],
    "max_complexity": DEFAULT_PROFILE[1],
    "max_params": DEFAULT_PROFILE[2],
    "max_nesting": DEFAULT_PROFILE[3],
}


# ------------------------------------------------------------- file handling


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_a.py",
        "src/a.spec.ts",
        "pkg/a_test.go",
        "src/test/java/AThing Test.java".replace(" ", ""),
        "spec/a_spec.rb",
        "src/__tests__/a.js",
    ],
)
def test_test_files_are_excluded(path):
    assert is_test_file(Path(path))


@pytest.mark.parametrize("path", ["src/a.py", "pkg/a.go", "src/latest.js", "lib/contest.rb"])
def test_source_files_are_kept(path):
    assert not is_test_file(Path(path))


def test_only_source_files_are_counted(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    write(tmp_path, "tests/test_a.py", "def test_a():\n    assert a() == 1\n")
    write(tmp_path, "README.md", "# hi\n")
    write(tmp_path, "node_modules/dep/index.js", "var x = 1;\n")
    stats = collect(tmp_path)
    assert stats["files"] == 1
    assert stats["functions"] == 1


# ----------------------------------------------------------------- metrics


def test_body_of_matches_braces():
    text = "func A() {\n\tif x {\n\t\ty()\n\t}\n}\nfunc B() {\n\tz()\n}\n"
    body = body_of(text, 0, "go")
    assert body.count("{") == body.count("}") == 2
    assert "func B" not in body


def test_body_of_follows_indentation():
    text = "def a():\n    x = 1\n    return x\n\ndef b():\n    return 2\n"
    body = body_of(text, 0, "python")
    assert "return x" in body and "def b" not in body


@pytest.mark.parametrize(
    "signature,expected",
    [
        ("def f():", 0),
        ("def f(a):", 1),
        ("def f(a, b, c):", 3),
        ("def f(a: dict[str, int], b=(1, 2)):", 2),
    ],
)
def test_count_params(signature, expected):
    assert count_params(signature) == expected


def test_nesting_depth_python_and_go():
    python = "def a():\n    if x:\n        for y in z:\n            w()\n"
    assert nesting_depth(python, "python") >= 2
    go = "func A() {\n\tif x {\n\t\tfor {\n\t\t\tw()\n\t\t}\n\t}\n}"
    assert nesting_depth(go, "go") >= 2


def test_complexity_counts_branches(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "def route(kind, flag):\n"
        "    if kind == 1:\n        return 'a'\n"
        "    elif kind == 2:\n        return 'b'\n"
        "    for item in flag:\n"
        "        while item:\n            item = item and other(item)\n"
        "    return None\n",
    )
    info = analyse_file(Path("a.py"), (tmp_path / "src/a.py").read_text(), "python", PROFILE)
    assert info["functions"][0]["complexity"] >= 6


def test_long_and_complex_functions_are_flagged(tmp_path):
    body = "".join(f"    if x == {i}:\n        y{i}()\n" for i in range(30))
    write(tmp_path, "src/a.py", f"def big(a):\n{body}    return 1\n")
    report = report_for(tmp_path)
    kinds = {f["kind"] for f in report["findings"]}
    assert {"long-function", "complex-function"} <= kinds
    assert dim(report, "kiss")["score"] < 0.5
    assert findings_of(report, "long-function")[0]["line"] == 1


def test_small_functions_score_well(tmp_path):
    for i in range(5):
        write(
            tmp_path,
            f"src/mod{i}.py",
            f"def add{i}(a, b):\n    return a + b\n\n\ndef sub{i}(a, b):\n    return a - b\n",
        )
    assert dim(report_for(tmp_path), "kiss")["score"] > 0.9


# --------------------------------------------------------------- profiles


def test_profile_blends_by_share_of_code():
    go_heavy = blend_profile({"go": 9000, "python": 1000})
    assert go_heavy["max_lines"] > blend_profile({"python": 9000})["max_lines"]
    assert go_heavy["languages"][0] == "go"


def test_profile_falls_back_for_unknown_languages():
    assert blend_profile({"cobol": 10})["max_lines"] == DEFAULT_PROFILE[0]
    assert blend_profile({})["languages"] == []


def test_thresholds_follow_the_language(tmp_path):
    body = "".join(f"\tx{i} := {i}\n" for i in range(45))
    write(tmp_path / "go", "src/a.go", f"func Big() int {{\n{body}\treturn 1\n}}\n")
    body_py = "".join(f"    x{i} = {i}\n" for i in range(45))
    write(tmp_path / "py", "src/a.py", f"def big():\n{body_py}    return 1\n")
    go = report_for(tmp_path / "go")
    py = report_for(tmp_path / "py")
    assert go["stats"]["profile"]["max_lines"] == 60
    assert py["stats"]["profile"]["max_lines"] == 40
    assert go["stats"]["long_functions"] == 0  # 47 lines is fine in Go
    assert py["stats"]["long_functions"] == 1  # and too long in Python


# ------------------------------------------------------------------- DRY


def test_duplicate_blocks_are_found(tmp_path):
    block = (
        "    total = compute(items)\n    if total > limit:\n        notify(user)\n"
        "    record = build(total)\n    store.save(record)\n    audit.log(record)\n"
        "    result = summarise(record)\n    return result\n"
    )
    write(tmp_path, "src/a.py", f"def one(items, limit, user):\n{block}")
    write(tmp_path, "src/b.py", f"def two(items, limit, user):\n{block}")
    report = report_for(tmp_path)
    assert report["stats"]["duplicate_lines"] >= 8
    assert findings_of(report, "duplicate-block")
    assert dim(report, "dry")["score"] < 1.0


def test_declaration_boilerplate_is_not_duplication():
    boilerplate = (
        "return &cobra.Command{\nUse: @,\nShort: @,\nLong: @,\n"
        "Args: cobra.NoArgs,\nHidden: false,\nSilenceUsage: true,\n}\n"
    )
    duplicates, findings = find_duplicate_blocks([("a.go", boilerplate), ("b.go", boilerplate)])
    assert duplicates == 0 and findings == []


def test_a_clean_codebase_scores_dry(tmp_path):
    for i in range(4):
        write(tmp_path, f"src/mod{i}.py", f"def unique{i}(value):\n    return value * {i + 2}\n")
    assert dim(report_for(tmp_path), "dry")["score"] == 1.0


# ------------------------------------------------------------------- SRP


def test_god_files_are_flagged(tmp_path):
    body = "".join(f"def helper{i}(a):\n    return a + {i}\n\n\n" for i in range(25))
    write(tmp_path, "src/everything.py", body)
    report = report_for(tmp_path)
    assert findings_of(report, "god-file")
    assert dim(report, "srp")["score"] < 1.0


def test_mixed_concerns_are_flagged(tmp_path):
    write(
        tmp_path,
        "src/all.py",
        "import psycopg2\nimport requests\nimport hashlib\n\n"
        "def handle(order):\n    return requests.get('http://x') and hashlib.md5(b'')\n",
    )
    assert findings_of(report_for(tmp_path), "mixed-concerns")


# ------------------------------------------------------------- OCP and LSP


def test_type_branching_lowers_ocp(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "def render(shape):\n"
        "    if shape.kind == 'circle':\n        return draw_circle(shape)\n"
        "    if shape.kind == 'square':\n        return draw_square(shape)\n"
        "    if isinstance(shape, Triangle):\n        return draw_triangle(shape)\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["type_switches"] >= 2
    assert report["stats"]["type_checks"] >= 1
    assert dim(report, "ocp")["score"] < 1.0


def test_lsp_is_not_scored_without_inheritance(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    report = report_for(tmp_path)
    assert dim(report, "lsp")["score"] is None
    assert "Liskov substitution" in report["not_scored"]


def test_unimplemented_overrides_lower_lsp(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "class Base:\n    def run(self):\n        return 1\n\n\n"
        "class Broken(Base):\n    def run(self):\n        raise NotImplementedError\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["subclasses"] == 1
    assert dim(report, "lsp")["score"] < 1.0


# --------------------------------------------------------------- ISP / DIP


def test_fat_interfaces_are_flagged(tmp_path):
    methods = "".join(f"    def method{i}(self):\n        ...\n" for i in range(9))
    write(tmp_path, "src/port.py", f"class Port(ABC):\n{methods}")
    report = report_for(tmp_path)
    assert findings_of(report, "fat-interface")
    assert dim(report, "isp")["score"] < 1.0


def test_isp_is_not_scored_without_interfaces(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    assert dim(report_for(tmp_path), "isp")["score"] is None


def test_infrastructure_spread_lowers_dip(tmp_path):
    concentrated = tmp_path / "clean"
    write(
        concentrated,
        "src/db.py",
        "import psycopg2\n\ndef connect():\n    return psycopg2.connect('')\n",
    )
    for i in range(5):
        write(
            concentrated, f"src/rule{i}.py", f"def rule{i}(order):\n    return order.total > {i}\n"
        )
    spread = tmp_path / "spread"
    for i in range(6):
        write(
            spread,
            f"src/rule{i}.py",
            f"import psycopg2\n\ndef rule{i}(order):\n"
            f"    conn = psycopg2.connect('')\n    return order.total > {i}\n",
        )
    assert dim(report_for(concentrated), "dip")["score"] > dim(report_for(spread), "dip")["score"]


# ------------------------------------------------------- coupling and GRASP


def test_find_cycles_detects_a_loop():
    cycles = find_cycles({"a": {"b"}, "b": {"c"}, "c": {"a"}})
    assert cycles and set(cycles[0][:-1]) == {"a", "b", "c"}


def test_find_cycles_ignores_a_dag():
    assert find_cycles({"a": {"b"}, "b": {"c"}, "c": set()}) == []


def test_import_cycles_are_flagged(tmp_path):
    write(tmp_path, "src/alpha.py", "from src import beta\n\ndef a():\n    return beta.b()\n")
    write(tmp_path, "src/beta.py", "from src import alpha\n\ndef b():\n    return alpha.a()\n")
    write(tmp_path, "src/gamma.py", "def c():\n    return 3\n")
    report = report_for(tmp_path)
    assert report["stats"]["cycles"]
    assert findings_of(report, "dependency-cycle")
    assert dim(report, "coupling")["score"] < 1.0


def test_coupling_is_not_scored_for_tiny_codebases(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    assert dim(report_for(tmp_path), "coupling")["score"] is None


def test_demeter_chains_are_counted(tmp_path):
    write(
        tmp_path, "src/a.py", "def total(order):\n    return order.customer.address.country.code\n"
    )
    report = report_for(tmp_path)
    assert report["stats"]["demeter_chains"] >= 1
    assert dim(report, "demeter")["score"] < 1.0


def test_cohesion_rewards_methods_that_use_their_state(tmp_path):
    write(
        tmp_path,
        "src/cart.py",
        "class Cart:\n"
        "    def __init__(self):\n        self.items = []\n        self.total = 0\n"
        "    def add(self, item):\n        self.items.append(item)\n"
        "    def sum(self):\n        return self.total\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["cohesion_classes"] == 1
    assert dim(report, "cohesion")["score"] > 0.9


def test_cohesion_is_not_scored_without_stateful_classes(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    assert dim(report_for(tmp_path), "cohesion")["score"] is None


# ---------------------------------------------------------- YAGNI & naming


def test_dead_private_code_is_flagged(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "def _never_called(value):\n    return value\n\n\ndef used(value):\n    return value\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["dead_symbols"] == 1
    assert findings_of(report, "dead-code")[0]["message"].startswith("`_never_called`")


def test_referenced_private_code_is_not_flagged(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "def _helper(value):\n    return value\n\n\ndef used(value):\n    return _helper(value)\n",
    )
    assert report_for(tmp_path)["stats"]["dead_symbols"] == 0


def test_stubs_and_commented_code_lower_yagni(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "# TODO: finish this\n"
        "# result = compute(value)\n"
        "# if result:\n"
        "def planned(value):\n    raise NotImplementedError\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["todos"] >= 1
    assert report["stats"]["commented_code"] >= 2
    assert dim(report, "yagni")["score"] < 1.0


def test_vague_names_and_flag_arguments_lower_naming(tmp_path):
    write(
        tmp_path,
        "src/a.py",
        "class DataManager:\n    pass\n\n\n"
        "def process(data, force=False):\n    return data\n\n\n"
        "def handle(item):\n    return item\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["vague_names"] >= 3
    assert report["stats"]["flag_params"] >= 1
    naming = dim(report, "naming")
    assert naming["score"] < 0.5
    assert "boolean flag parameter" in naming["detail"]


def test_clear_names_score_well(tmp_path):
    write(
        tmp_path,
        "src/pricing.py",
        "class PriceList:\n    pass\n\n\n"
        "def apply_discount(order, percentage):\n    return order * percentage\n",
    )
    assert dim(report_for(tmp_path), "naming")["score"] == 1.0


# ------------------------------------------------------- scanner accuracy
#
# The metrics are regex-based and cross-language, so they are checked against
# Python's `ast` — a real parser — on the one language where an oracle is
# available. If the numbers track a parser here, the same scanner is doing the
# same job for Go and Java, where no stdlib parser exists to check them with.


def complexity_via_ast(source):
    tree = ast.parse(source)
    decisions = 0
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)
        ):
            decisions += 1
        elif isinstance(node, ast.BoolOp):
            decisions += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            decisions += len(node.ifs)
        elif hasattr(ast, "match_case") and isinstance(node, ast.match_case):
            decisions += 1
    return decisions + 1


def params_via_ast(source):
    function = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    args = function.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    if names and names[0] in {"self", "cls"}:
        names = names[1:]
    return len(names) + bool(args.vararg) + bool(args.kwarg)


SAMPLES = [
    "def plain(a, b):\n    return a + b\n",
    (
        "def branching(order, user):\n"
        "    if order.total > 100 and user.member:\n        return 'a'\n"
        "    elif order.total > 50 or user.trial:\n        return 'b'\n"
        "    for line in order.lines:\n"
        "        while line.pending:\n            line.settle()\n"
        "    return None\n"
    ),
    (
        "def guarded(values):\n"
        "    try:\n        return [v for v in values if v]\n"
        "    except ValueError:\n        return []\n"
    ),
    ("def method(self, alpha, beta=1, *rest, **options):\n    return alpha\n"),
]


@pytest.mark.parametrize("source", SAMPLES)
def test_complexity_tracks_a_real_parser(source):
    measured = analyse_file(Path("x.py"), source, "python", PROFILE)["functions"][0]["complexity"]
    assert abs(measured - complexity_via_ast(source)) <= 1


@pytest.mark.parametrize("source", SAMPLES)
def test_parameter_count_matches_a_real_parser(source):
    measured = analyse_file(Path("x.py"), source, "python", PROFILE)["functions"][0]["params"]
    assert measured == params_via_ast(source)


@pytest.mark.parametrize(
    "lang,name,source",
    [
        (
            "python",
            "x.py",
            (
                "def render(kind):\n"
                '    """If a circle, for squares, while triangles, and or."""\n'
                "    return TEMPLATE % kind\n"
            ),
        ),
        (
            "javascript",
            "x.js",
            (
                "function get() {\n  // if the url has a query, and or while\n"
                '  return fetch("http://x.com/a?b=1");\n}\n'
            ),
        ),
        (
            "go",
            "x.go",
            'func Get() string {\n\t/* if and or while */\n\treturn "if for while and or"\n}\n',
        ),
    ],
)
def test_prose_does_not_add_branches(lang, name, source):
    info = analyse_file(Path(name), source, lang, PROFILE)
    assert info["functions"][0]["complexity"] == 1


def test_braces_inside_strings_do_not_break_body_extraction():
    source = 'func A() string {\n\treturn "}{"\n}\n\nfunc B() int {\n\treturn 2\n}\n'
    info = analyse_file(Path("x.go"), source, "go", PROFILE)
    assert [f["name"] for f in info["functions"]] == ["A", "B"]
    assert info["functions"][0]["lines"] == 3


def test_urls_are_not_read_as_comments():
    source = 'const a = "http://x.com";\nfunction used(value) {\n  return value;\n}\n'
    info = analyse_file(Path("x.js"), source, "javascript", PROFILE)
    assert any(f["name"] == "used" for f in info["functions"])


def test_dots_inside_strings_are_not_demeter_chains():
    source = 'def log():\n    return "a.b.c.d.e"\n'
    assert analyse_file(Path("x.py"), source, "python", PROFILE)["demeter"] == 0


def test_strip_noise_preserves_offsets_and_lines():
    source = 'x = "abc" # note\ny = 2\n'
    stripped = strip_noise(source, "python")
    assert len(stripped) == len(source)
    assert stripped.count("\n") == source.count("\n")
    assert "abc" not in stripped and "note" not in stripped


# --------------------------------------------------------- parameter counting


@pytest.mark.parametrize(
    "lang,name,source,expected",
    [
        # `self` is not a parameter the caller passes
        ("python", "x.py", "def method(self, a, b):\n    return a\n", 2),
        # a wrapped signature is exactly the case where the count matters
        (
            "python",
            "x.py",
            (
                "def wrapped(\n    alpha,\n    beta,\n    gamma,\n    delta,\n"
                "    epsilon,\n    zeta,\n):\n    return 1\n"
            ),
            6,
        ),
        # the Go receiver is not the parameter list
        (
            "go",
            "x.go",
            "func (r *Repo) Save(ctx context.Context, o Order) error {\n\treturn nil\n}\n",
            2,
        ),
        (
            "java",
            "X.java",
            "public void configure(String a, int b, boolean c) {\n  return;\n}\n",
            3,
        ),
        ("python", "x.py", "def none():\n    return 1\n", 0),
        # a comma inside generics is not a parameter separator
        (
            "typescript",
            "x.ts",
            "function pick(items: Map<string, number>, key: string) {\n  return 1;\n}\n",
            2,
        ),
    ],
)
def test_parameter_counting(lang, name, source, expected):
    info = analyse_file(Path(name), source, lang, PROFILE)
    assert info["functions"][0]["params"] == expected


def test_wrapped_signatures_still_trip_the_limit(tmp_path):
    params = "".join(f"    arg{i},\n" for i in range(8))
    write(tmp_path, "src/a.py", f"def build(\n{params}):\n    return 1\n")
    report = report_for(tmp_path)
    assert report["stats"]["wide_functions"] == 1
    assert findings_of(report, "many-parameters")


# ------------------------------------------------------------ generated code


@pytest.mark.parametrize(
    "name,text",
    [
        ("api.pb.go", "package api\n"),
        ("model_pb2.py", "x = 1\n"),
        ("thing.g.dart", "class X {}\n"),
        ("app.min.js", "var a=1;" * 200),
        ("wire.go", "// Code generated by protoc. DO NOT EDIT.\npackage wire\n"),
        ("bundle.js", "/* @generated */\nvar a = 1;\n"),
    ],
)
def test_generated_files_are_recognised(name, text):
    assert is_generated(Path(name), text)


@pytest.mark.parametrize(
    "name,text",
    [
        ("billing.py", "def charge(amount):\n    return amount\n"),
        ("generator.py", "def generate(seed):\n    return seed\n"),
    ],
)
def test_handwritten_files_are_not_skipped(name, text):
    assert not is_generated(Path(name), text)


def test_generated_files_are_excluded_from_the_score(tmp_path):
    write(tmp_path, "src/real.py", "def charge(amount):\n    return amount\n")
    body = "".join(f"    if x == {i}:\n        y()\n" for i in range(40))
    write(tmp_path, "src/api_pb2.py", f"# @generated\ndef huge(a, b, c, d, e, f, g):\n{body}")
    stats = collect(tmp_path)
    assert stats["files"] == 1
    assert stats["generated_skipped"] == 1
    assert stats["long_functions"] == 0  # the generated monster is not counted
    assert "generated file(s) skipped" in render_text(evaluate(stats))


# ------------------------------------------------- hotspots (churn x complexity)


def git_repo(path):
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@e",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e",
        "PATH": "/usr/bin:/bin",
    }
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)
    return env


def commit(path, env, message):
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", message], check=True, env=env)


def complex_body(revision):
    body = "".join(
        f"    if kind == {i}:\n        for row in rows:\n            total += {i}\n"
        for i in range(12)
    )
    return f"def route(kind, rows, total):\n{body}    return total + {revision}\n"


def churned_repo(tmp_path, hot_is_complex=True):
    env = git_repo(tmp_path)
    for i in range(6):
        write(tmp_path, f"src/quiet{i}.py", f"def calc{i}(a, b):\n    return a + b + {i}\n")
    write(
        tmp_path,
        "src/billing.py",
        complex_body(0) if hot_is_complex else "def route(a):\n    return a\n",
    )
    write(
        tmp_path,
        "src/orders.py",
        complex_body(0) if hot_is_complex else "def place(a):\n    return a\n",
    )
    if not hot_is_complex:
        write(tmp_path, "src/tangle.py", complex_body(0))
    commit(tmp_path, env, "init")
    for revision in range(1, 8):
        write(
            tmp_path,
            "src/billing.py",
            complex_body(revision)
            if hot_is_complex
            else f"def route(a):\n    return a + {revision}\n",
        )
        write(
            tmp_path,
            "src/orders.py",
            complex_body(revision)
            if hot_is_complex
            else f"def place(a):\n    return a + {revision}\n",
        )
        write(tmp_path, "src/quiet0.py", f"def calc0(a, b):\n    return a + b + {revision}\n")
        commit(tmp_path, env, f"change {revision}")
    return tmp_path


def test_git_churn_counts_commits_per_file(tmp_path):
    repo = churned_repo(tmp_path)
    churn = git_churn(repo)
    assert churn["src/billing.py"] == 8
    assert churn["src/quiet5.py"] == 1


def test_git_churn_strips_the_subdirectory_prefix(tmp_path):
    repo = churned_repo(tmp_path)
    # Scanning a subdirectory: git reports repo-root paths, the scan uses
    # subdirectory-relative ones, and they have to be made to meet.
    churn = git_churn(repo / "src")
    assert "billing.py" in churn and "src/billing.py" not in churn


def test_git_churn_is_empty_outside_a_repository(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    assert git_churn(tmp_path) == {}


def test_complexity_that_sits_where_the_changes_land_scores_badly(tmp_path):
    report = report_for(churned_repo(tmp_path))
    hotspots = dim(report, "hotspots")
    assert hotspots["score"] is not None and hotspots["score"] < 0.4
    assert "most-changed files average" in hotspots["detail"]
    flags = findings_of(report, "hotspot")
    assert {f["file"] for f in flags} >= {"src/billing.py", "src/orders.py"}
    assert "changed 8 times" in flags[0]["message"]


def test_complexity_away_from_the_changes_scores_well(tmp_path):
    report = report_for(churned_repo(tmp_path, hot_is_complex=False))
    assert dim(report, "hotspots")["score"] > 0.8
    assert not findings_of(report, "hotspot")


def test_hotspots_are_not_scored_without_history(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    report = report_for(tmp_path)
    assert dim(report, "hotspots")["score"] is None
    assert "Hotspots (churn x complexity)" in report["not_scored"]


def test_find_hotspots_needs_enough_files_and_churn():
    assert find_hotspots({"a.py": 9}, {"a.py": 30}) is None  # one file
    assert (
        find_hotspots({f"f{i}.py": 1 for i in range(6)}, {f"f{i}.py": 5 for i in range(6)}) is None
    )  # no churn


# --------------------------------------------------------- duplication bounds


def test_duplicated_lines_never_exceed_the_file(tmp_path):
    block = "".join(f"    step{i} = compute({i}) + offset\n" for i in range(10))
    write(tmp_path, "src/a.py", f"def one(offset):\n{block}    return step0\n")
    write(tmp_path, "src/b.py", f"def two(offset):\n{block}    return step0\n")
    stats = collect(tmp_path)
    assert 0 < stats["duplicate_lines"] <= stats["lines"]


# ------------------------------------------------------------------ report


def test_score_is_bounded_and_ordered(tmp_path):
    good = tmp_path / "good"
    for i in range(4):
        write(
            good,
            f"src/mod{i}.py",
            f"def apply_rate{i}(amount, rate):\n    return amount * rate + {i}\n",
        )
    bad = tmp_path / "bad"
    body = "".join(
        f"    if kind == {i}:\n        for row in rows:\n            total = total + {i}\n"
        for i in range(25)
    )
    write(
        bad, "src/everything.py", f"def process(data, force=False):\n{body}    return total\n" * 2
    )

    good_report, bad_report = report_for(good), report_for(bad)
    assert 0 <= good_report["score"] <= 100
    assert 0 <= bad_report["score"] <= 100
    assert good_report["score"] > bad_report["score"]
    assert good_report["grade"] in {"A", "B"}


def test_recommendations_are_ranked(tmp_path):
    body = "".join(f"    if x == {i}:\n        y()\n" for i in range(30))
    write(tmp_path, "src/a.py", f"def big(a):\n{body}    return 1\n")
    wins = recommendations(report_for(tmp_path))
    assert wins and [w["lost"] for w in wins] == sorted((w["lost"] for w in wins), reverse=True)


def test_renderers_contain_the_essentials(tmp_path):
    write(tmp_path, "src/a.py", "def a(value):\n    return value\n")
    report = report_for(tmp_path)
    text = render_text(report)
    assert "gradebook-code" in text and "SCORE" in text and "Simplicity (KISS)" in text
    markdown = render_markdown(report)
    assert "| Principle |" in markdown and "Code score" in markdown


def test_by_dir_ranks_the_worst_first(tmp_path):
    good = tmp_path / "good"
    write(good, "a.py", "def add(a, b):\n    return a + b\n")
    bad = tmp_path / "bad"
    body = "".join(f"    if x == {i}:\n        y()\n" for i in range(30))
    write(bad, "b.py", f"def big(a):\n{body}    return 1\n")
    ranked = score_directories(tmp_path)
    assert [entry["path"] for entry in ranked] == ["bad", "good"]


# --------------------------------------------------------------------- cli


def test_cli_json_and_gates(tmp_path, capsys):
    body = "".join(f"    if x == {i}:\n        y()\n" for i in range(30))
    write(tmp_path, "src/a.py", f"def big(a):\n{body}    return 1\n")
    assert main([str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["score"] < 100 and payload["findings"]

    assert main([str(tmp_path), "--fail-under", "99"]) == 1
    assert main([str(tmp_path), "--fail-under", "0"]) == 0


def test_cli_baseline_gate(tmp_path, capsys):
    write(tmp_path, "src/a.py", "def add(a, b):\n    return a + b\n")
    assert main([str(tmp_path), "--format", "json"]) == 0
    baseline = tmp_path / "baseline.json"
    baseline.write_text(capsys.readouterr().out)

    assert main([str(tmp_path), "--baseline", str(baseline), "--fail-on-drop"]) == 0
    body = "".join(f"    if x == {i}:\n        y()\n" for i in range(30))
    write(tmp_path, "src/b.py", f"def big(a, force=False):\n{body}    return 1\n")
    assert main([str(tmp_path), "--baseline", str(baseline), "--fail-on-drop"]) == 1


def test_cli_rejects_bad_input(tmp_path):
    assert main([str(tmp_path / "missing")]) == 2
    assert main([str(tmp_path), "--fail-on-drop"]) == 2
    assert main([str(tmp_path), "--baseline", str(tmp_path / "nope.json")]) == 2


def test_cli_lists_dimensions(capsys):
    assert main(["--list-dimensions"]) == 0
    assert "Simplicity (KISS)" in capsys.readouterr().out
