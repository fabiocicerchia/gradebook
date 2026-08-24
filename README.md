# gradebook

[![CI](https://github.com/fabiocicerchia/gradebook/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/gradebook/actions/workflows/ci.yml)
[![Code Quality](https://github.com/fabiocicerchia/gradebook/actions/workflows/code-quality.yml/badge.svg)](https://github.com/fabiocicerchia/gradebook/actions/workflows/code-quality.yml)
[![Security](https://github.com/fabiocicerchia/gradebook/actions/workflows/security.yml/badge.svg)](https://github.com/fabiocicerchia/gradebook/actions/workflows/security.yml)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/fabiocicerchia/gradebook/badge)](https://securityscorecards.dev/viewer/?uri=github.com/fabiocicerchia/gradebook)
[![CI carbon](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fabiocicerchia/gradebook/gh-pages/badge.json)](.github/workflows/carbon-badge.yml)

Two tools that grade a repository against a weighted rubric and tell you which
fix buys the most points. **`gradebook-tests`** scores the test suite;
**`gradebook-code`** scores the code it covers. They are independent programs in
sibling folders — install one, both, or neither — sharing only these docs, a
Makefile and a CI job.

```sh
gradebook-tests .        # is this suite worth anything?
gradebook-code .         # is this code worth testing?
```

Neither needs config, a build, or a test run: each is a read-only pass over the
working tree (plus `git log`), standard library only, across Python, JS/TS, Go,
Java/Kotlin, Ruby, PHP, Rust, C#, Elixir, Scala and more.

```console
$ gradebook-code .
gradebook-code 0.1.0 — /srv/mockterview
languages: go (22)  ·  calibrated for go: 60 lines, complexity 12, 5 params

  Simplicity (KISS)              ████████████████████  13.7/14  3.9 average complexity over 100 functions
  Duplication (DRY)              ████████████████████  12.0/12  0.0% of lines duplicated elsewhere
  Cohesion (GRASP)               ····················   n/a /7   no classes with shared state to judge
  Naming & intent                █████████████░░░░░░░   4.0/6   7/141 vague names (manager, helper, data, …)
  ...

SCORE  95.4/100   grade A
not scored (weights redistributed): Cohesion (GRASP)

Biggest wins:
  +2.0   Naming & intent — name things for what they are: a Manager or a Helper is a class nobody could describe
  +1.5   Dependency inversion — concentrate infrastructure behind a few adapters and inject it

Red flags (1):
  internal/tui/update.go:12  complex-function   `Update` has 13 complexity (limit 12)
```

## What they share

Both follow the same shape, so learning one teaches you the other:

- **A weighted model that adds to 100**, with letter grades: **A** ≥85, **B** ≥70,
  **C** ≥55, **D** ≥40, **F** below.
- **Dimensions with no evidence are not scored** rather than scored zero — no
  git history, no interfaces, no inheritance — and the remaining weights
  renormalise. The report names them, so a missing signal never quietly
  inflates or sinks the number.
- **Per-language calibration.** Thresholds are weighted by how much of the repo
  each language is, and the calibration is printed next to the languages. A
  47-line function is unremarkable in Go and too long in Python.
- **Red flags with `file:line`.** A score is not actionable; `src/billing.py:42`
  is. Both tools rank findings by severity and print them under the score.
- **The same flags**: `--format {text,json,markdown}`, `--by-dir` for monorepos,
  `--fail-under N`, and `--baseline report.json --fail-on-drop` to gate CI on
  the trend instead of an absolute bar most repos cannot clear on day one.

## Install

```sh
pipx install ./gradebook-tests
pipx install ./gradebook-code
```

Python 3.10+, no dependencies. From a checkout: `make dev`.

## Usage

```sh
gradebook-tests .                     # score the repo you are in
gradebook-code ../other-repo          # score anything, no setup needed
gradebook-code . --by-dir             # per subproject, worst first
gradebook-tests . --format markdown   # paste-ready PR comment
gradebook-tests . --list-dimensions   # the scoring model
```

More in [`docs/getting-started.md`](docs/getting-started.md).

## In CI

The useful gate is *do not get worse*, not an absolute bar:

```sh
gradebook-code . --format json > baseline.json     # once, on the default branch
gradebook-code . --baseline baseline.json --fail-on-drop
```

More in [`docs/ci.md`](docs/ci.md).

## Documentation

Full docs live in [`docs/`](docs/) (also published via mkdocs). Runnable
examples live in [`examples/`](examples/).

- [gradebook-tests](docs/gradebook-tests.md) — the 18 dimensions, how tests are found and classified, caveats.
- [gradebook-code](docs/gradebook-code.md) — the 13 principle dimensions, what each one actually measures.
- [Anti-patterns](docs/anti-patterns.md) — the ten red-flag detectors and the catalogue behind the model.
- [Gating CI](docs/ci.md) — trend gates, absolute bars, monorepos.
- [Architecture](docs/architecture.md) — how a score is assembled.
- [Status & roadmap](docs/roadmap.md) — what works today, what is next.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md). gradebook uses
[Conventional Commits](https://www.conventionalcommits.org/) and release-please.

## Security

Found a vulnerability? See [SECURITY.md](SECURITY.md) — please don't open a
public issue.

## Support

Need help implementing this? [Get in touch](https://fabiocicerchia.it/contact).

## License

[Apache 2.0](LICENSE) © 2026 Fabio Cicerchia
