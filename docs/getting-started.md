# Getting Started

## Prerequisites

- **Python 3.10+**. Nothing else — both tools are standard library only.
- `git` on `$PATH` if you want the history-based dimensions (TDD discipline in
  `gradebook-tests`, churn-weighted hotspots in `gradebook-code`). Without a
  repository those dimensions are dropped as unscored and the remaining weights
  renormalise — `gradebook-tests --no-git` skips them deliberately.

## Install

Both tools are ordinary Python packages, so `pip` installs them and so does
`pipx`. Reach for `pipx` when you want the two commands on `$PATH` without
touching any project's environment; reach for `pip` when you want them *inside*
one — a virtualenv, a CI job, a Docker layer. The arguments below are identical
either way.

Neither package is on PyPI yet, so there is no bare `pip install gradebook-code`
to run — the repository is the package. From a checkout:

```sh
git clone https://github.com/fabiocicerchia/gradebook
pip install ./gradebook/gradebook-tests
pip install ./gradebook/gradebook-code
```

Or without one. Each tool is a subdirectory of the same repository, which is
what `#subdirectory=` tells pip:

```sh
pip install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-tests"
pip install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-code"
```

Quote the whole spec — `#` starts a comment in most shells. That form tracks
the default branch; pin a release with `@<tag>` before the fragment, which is
what you want in CI:

```sh
pip install "git+https://github.com/fabiocicerchia/gradebook.git@v0.4.0#subdirectory=gradebook-code"
```

The tags are on the
[releases page](https://github.com/fabiocicerchia/gradebook/releases).

Install one, both, or neither: they are independent programs and a missing one
never stops the other from scoring.

Check it landed — and note the man page rides along in the wheel, so a system
or `--user` install puts `gradebook-code(1)` on the default manpath:

```sh
gradebook-code --version
gradebook-tests --help
man gradebook-code
```

To remove them, `pip uninstall gradebook-tests gradebook-code` (the
distribution names, with hyphens; `pipx uninstall` takes one at a time).

### Development in this repo

```sh
make setup   # editable installs of both, dev tooling, pre-commit hook
make test    # both suites
make lint    # the whole gate
```

`make install` is the non-editable equivalent: a plain `pip install` of both
directories.

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
