"""The command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .base import VERSION, Report
from .collect import collect
from .render import render_markdown, render_text, score_directories
from .score import DIMENSIONS, evaluate, recommendations

# ---------------------------------------------------------------------- cli


def _build_parser() -> argparse.ArgumentParser:
    """The CLI surface, in one place."""
    parser = argparse.ArgumentParser(
        prog="gradebook-code",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="codebase to evaluate")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fail-under", type=float, metavar="N", help="exit 1 when the score is below N (CI gate)")
    parser.add_argument("--baseline", metavar="FILE", help="a previous --format json report to diff against")
    parser.add_argument(
        "--fail-on-drop",
        type=float,
        nargs="?",
        const=0.0,
        metavar="N",
        help="with --baseline, exit 1 when the score drops by more than N",
    )
    parser.add_argument(
        "--by-dir",
        action="store_true",
        help="also score each immediate subdirectory that holds code",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="how many recommendations to show (default 5)",
    )
    parser.add_argument(
        "--max-flags",
        type=int,
        default=None,
        metavar="N",
        help="cap the red flags listed (default: all, 0 to hide)",
    )
    parser.add_argument("--list-dimensions", action="store_true", help="print the scoring model and exit")
    parser.add_argument("--version", action="version", version=f"gradebook-code {VERSION}")
    return parser


def _emit(report: Report, args: argparse.Namespace) -> None:
    """The report, in whichever format was asked for."""
    if args.format == "json":
        json.dump(report, sys.stdout, indent=2, default=str)
        print()  # noqa: T201 — the tool's output
    elif args.format == "markdown":
        print(render_markdown(report, args.top, args.max_flags))  # noqa: T201 — the tool's output
    else:
        text = render_text(report, args.top, args.max_flags)
        if "baseline" in report:
            text = text.replace(
                f"grade {report['grade']}",
                f"grade {report['grade']}   {report['baseline']['delta']:+.1f} vs baseline "
                f"({report['baseline']['score']:.1f})",
                1,
            )
        print(text)  # noqa: T201 — the tool's output


def _gate_failed(report: Report, args: argparse.Namespace) -> bool:
    """Whether either gate — a floor, or a drop against a baseline — was
    crossed. Says which on stderr, since that is the whole point of a gate."""
    failed = False
    if args.fail_under is not None and report["score"] < args.fail_under:
        print(  # noqa: T201 — the tool's output
            f"gradebook-code: {report['score']:.1f} is below --fail-under {args.fail_under}",
            file=sys.stderr,
        )
        failed = True
    if args.fail_on_drop is not None:
        drop = -report["baseline"]["delta"]
        if drop > args.fail_on_drop:
            print(f"gradebook-code: dropped {drop:.1f} points against the baseline", file=sys.stderr)  # noqa: T201 — the tool's output
            failed = True
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_dimensions:
        for key, title, weight in DIMENSIONS:
            print(f"{key:<10} {weight:>3} pts  {title}")  # noqa: T201 — the tool's output
        print(  # noqa: T201 — the tool's output
            "\nAny dimension without evidence (no interfaces, no inheritance, too few "
            "modules)\nis left unscored and the remaining weights renormalise."
        )
        return 0
    if args.fail_on_drop is not None and not args.baseline:
        print("gradebook-code: --fail-on-drop needs --baseline", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    root = Path(args.path)
    if not root.is_dir():
        print(f"gradebook-code: not a directory: {root}", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    report = evaluate(collect(root))
    report["recommendations"] = [
        {"dimension": d["id"], "points": d["lost"], "advice": d["advice"]} for d in recommendations(report, args.top)
    ]
    if args.by_dir:
        report["directories"] = score_directories(root)
    if args.baseline:
        try:
            baseline = json.loads(Path(args.baseline).read_text())
            report["baseline"] = {
                "score": baseline["score"],
                "delta": round(report["score"] - baseline["score"], 1),
            }
        except (OSError, ValueError, KeyError) as error:
            print(f"gradebook-code: cannot read baseline {args.baseline}: {error}", file=sys.stderr)  # noqa: T201 — the tool's output
            return 2

    _emit(report, args)

    return 1 if _gate_failed(report, args) else 0


if __name__ == "__main__":
    sys.exit(main())
