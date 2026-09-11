# Getting Started

## Prerequisites

- **Python 3.10+**. Nothing else — both tools are standard library only.
- `git` on `$PATH` if you want the history-based dimensions (TDD discipline in
  `gradebook-tests`, churn-weighted hotspots in `gradebook-code`). Without a
  repository those dimensions are dropped as unscored and the remaining weights
  renormalise — `gradebook-tests --no-git` skips them deliberately.

## Install

These are command-line tools, so **`pipx` is the installer to reach for**: it
gives each one its own virtualenv and puts the command on `$PATH`, without
touching any project's environment — and it is the form that works on Debian,
Ubuntu, Fedora and Homebrew Python, where installing into the system
interpreter is refused outright (see [below](#error-externally-managed-environment)).

Neither package is on PyPI yet, so there is no bare `pipx install
gradebook-code` to run — the repository is the package, and each tool is a
subdirectory of it, which is what `#subdirectory=` says:

```sh
pipx install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-tests"
pipx install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-code"
```

Quote the whole spec — `#` starts a comment in most shells. From a checkout,
the directory is the package:

```sh
git clone https://github.com/fabiocicerchia/gradebook
pipx install ./gradebook/gradebook-tests
pipx install ./gradebook/gradebook-code
```

Install one, both, or neither: they are independent programs and a missing one
never stops the other from scoring.

One exception to all of this: the **VS Code extension imports the two modules**
rather than running the commands, so a sealed pipx virtualenv is not enough for
it on its own — see [Editor integration](editors.md#vs-code). The Neovim plugin
shells out to the CLIs, so pipx suits it fine.

### With pip, inside an environment

`pip` takes exactly the same arguments, and is the right tool when you want the
commands *inside* a particular environment rather than on `$PATH` — a
virtualenv, a CI job, a Docker layer:

```sh
python3 -m venv .venv
.venv/bin/pip install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-code"
.venv/bin/gradebook-code .
```

### Pin a release

Every form above tracks the default branch. Put `@<tag>` before the fragment to
pin one instead, which is what you want in CI — either installer takes it:

```sh
pipx install "git+https://github.com/fabiocicerchia/gradebook.git@v0.4.0#subdirectory=gradebook-code"
```

The tags are on the
[releases page](https://github.com/fabiocicerchia/gradebook/releases).

### `error: externally-managed-environment`

```text
error: externally-managed-environment

× This environment is externally managed
```

That is [PEP 668](https://peps.python.org/pep-0668/), and it is pip refusing to
install into the interpreter your distribution's own packages depend on —
Debian, Ubuntu, Fedora and Homebrew all ship one. It is not about these tools;
`pip install --user` is refused for the same reason.

Use `pipx`, which sidesteps it by building a virtualenv per tool, or a venv of
your own — both are above. `--break-system-packages` does force it through, but
that flag is the risk the message is warning you about, not a fix for it.

### Check it landed

```sh
gradebook-code --version
gradebook-tests --help
man gradebook-code
```

The man page rides along in the wheel. `pipx` puts it where `man` looks;
a system or `--user` install lands it on the default manpath; inside a
virtualenv it sits under `.venv/share/man` and `man` will not find it unless
you point `MANPATH` there.

To remove them: `pipx uninstall gradebook-code` (one at a time), or
`pip uninstall gradebook-tests gradebook-code` — the distribution names, with
hyphens.

### Development in this repo

```sh
make setup   # editable installs of both, dev tooling, pre-commit hook
make test    # both suites
make lint    # the whole gate
```

`make install` is the non-editable equivalent: a plain `pip install` of both
directories. Both run pip against whichever interpreter is active, so run them
in a virtualenv.

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
