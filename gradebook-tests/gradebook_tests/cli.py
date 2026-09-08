"""The command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .base import VERSION, Report
from .collection import collect
from .render import render_markdown, render_text
from .score import DIMENSIONS, compare, evaluate, recommendations, score_directories

# ---------------------------------------------------------------------- cli


def _build_parser() -> argparse.ArgumentParser:
    """The CLI surface, in one place."""
    parser = argparse.ArgumentParser(
        prog="gradebook-tests",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="repository to evaluate")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fail-under", type=float, metavar="N", help="exit 1 when the score is below N (CI gate)")
    parser.add_argument("--baseline", metavar="FILE", help="a previous --format json report to diff against")
    parser.add_argument(
        "--fail-on-drop",
        type=float,
        nargs="?",
        const=0.0,
        metavar="N",
        help="with --baseline, exit 1 when the score drops by more than N (default 0)",
    )
    parser.add_argument(
        "--max-flags",
        type=int,
        default=None,
        metavar="N",
        help="cap the red flags listed (default: all, 0 to hide)",
    )
    parser.add_argument(
        "--by-dir",
        action="store_true",
        help="also score each immediate subdirectory that holds code",
    )
    parser.add_argument("--no-git", action="store_true", help="skip the git-history TDD analysis")
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="how many recommendations to show (default 5)",
    )
    parser.add_argument("--list-dimensions", action="store_true", help="print the scoring model and exit")
    parser.add_argument("--version", action="version", version=f"gradebook-tests {VERSION}")
    return parser


def _emit(report: Report, args: argparse.Namespace) -> None:
    """The report, in whichever format was asked for."""
    if args.format == "json":
        json.dump(report, sys.stdout, indent=2, sort_keys=False)
        print()  # noqa: T201 — the tool's output
    elif args.format == "markdown":
        print(render_markdown(report, args.top, args.max_flags))  # noqa: T201 — the tool's output
    else:
        print(render_text(report, args.top, args.max_flags))  # noqa: T201 — the tool's output


def _gate_failed(report: Report, args: argparse.Namespace) -> bool:
    """Whether either gate — a floor, or a drop against a baseline — was
    crossed. Says which on stderr, since that is the whole point of a gate."""
    failed = False
    if args.fail_under is not None and report["score"] < args.fail_under:
        print(  # noqa: T201 — the tool's output
            f"gradebook-tests: {report['score']:.1f} is below --fail-under {args.fail_under}",
            file=sys.stderr,
        )
        failed = True
    if args.fail_on_drop is not None:
        drop = -report["baseline"]["delta"]
        if drop > args.fail_on_drop:
            print(  # noqa: T201 — the tool's output
                f"gradebook-tests: dropped {drop:.1f} points against the baseline (tolerance {args.fail_on_drop})",
                file=sys.stderr,
            )
            failed = True
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_dimensions:
        for key, title, weight in DIMENSIONS:
            note = "  (only when a mutation report exists)" if key == "mutation" else ""
            print(f"{key:<12} {weight:>3} pts  {title}{note}")  # noqa: T201 — the tool's output
        print(  # noqa: T201 — the tool's output
            "\nThe always-scored dimensions total 100; any dimension that cannot be "
            "judged is\nleft unscored and the remaining weights renormalise."
        )
        return 0

    root = Path(args.path)
    if not root.is_dir():
        print(f"gradebook-tests: not a directory: {root}", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    if args.fail_on_drop is not None and not args.baseline:
        print("gradebook-tests: --fail-on-drop needs --baseline", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    stats = collect(root, use_git=not args.no_git)
    report = evaluate(stats)
    report["recommendations"] = [
        {"dimension": d["id"], "points": d["lost"], "advice": d["advice"]} for d in recommendations(report, args.top)
    ]
    if args.by_dir:
        report["directories"] = score_directories(root, use_git=not args.no_git)
    if args.baseline:
        try:
            compare(report, json.loads(Path(args.baseline).read_text()))
        except (OSError, ValueError) as error:
            print(f"gradebook-tests: cannot read baseline {args.baseline}: {error}", file=sys.stderr)  # noqa: T201 — the tool's output
            return 2

    _emit(report, args)

    return 1 if _gate_failed(report, args) else 0


if __name__ == "__main__":
    sys.exit(main())
