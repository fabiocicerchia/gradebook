# Getting Started

## Prerequisites

- **Python 3.10+**. Nothing else — both tools are standard library only.
- `git` on `$PATH` if you want the history-based dimensions (TDD discipline in
  `gradebook-tests`, churn-weighted hotspots in `gradebook-code`). Without a
  repository those dimensions are dropped as unscored and the remaining weights
  renormalise — `gradebook-tests --no-git` skips them deliberately.

## Setup

Install either tool, or both:

```sh
pipx install ./gradebook-tests
pipx install ./gradebook-code
```

For development in this repo:

```sh
make dev     # editable installs of both, plus pytest and ruff
make test    # both suites
make lint
```

## Run

Neither tool needs config, a build, or a test run — point it at a path:

```sh
gradebook-tests .              # is this suite worth anything?
gradebook-code .               # is this code worth testing?
gradebook-code ../other-repo   # anything, no setup needed
```

Read the red flags, not just the number: each one carries a `file:line`, and
they are ranked by severity.

```sh
gradebook-tests . --max-flags 10       # cap the list (default: all)
gradebook-tests . --list-dimensions    # the scoring model, weight by weight
gradebook-tests . --by-dir             # per subproject, worst first — for monorepos
```

## Gate a pull request

The regression gate is the one most repos can switch on today: it fails when
the repo gets *worse*, not when it is merely imperfect.

```sh
gradebook-code . --format json > baseline.json     # once, on the default branch
gradebook-code . --baseline baseline.json --fail-on-drop
```

Absolute bars, PR comments and the monorepo breakdown are in
[Gating CI](ci.md).

## Reading the score

A ≥85, B ≥70, C ≥55, D ≥40, F below. A dimension with no evidence in the repo
is **not scored** rather than scored zero, and the report names it — so a
missing signal never quietly inflates or sinks the number.

A low score is an argument, not a verdict. Generated code, an interpreter loop,
a parser table and a state machine all score badly for good reasons.
