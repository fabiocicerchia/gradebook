# gradebook-tests — is this suite worth anything?

Coverage percentage tells you which lines ran, not whether your suite would
catch a regression. `gradebook-tests` walks any repository, finds and classifies
its tests (unit, integration, functional/E2E, BDD), reads whatever coverage
evidence actually exists, mines git history for TDD discipline, judges whether
test names describe behaviour, tells a real assertion from one that accepts
anything, checks whether mocks and stubs sit at real seams, hunts down the
tests that were written to satisfy a checkbox, and grades it **0-100** — then
tells you which fix buys the most points and which files to open first.

No config, no language server, no test run: it is a read-only pass over the
working tree plus `git log`, and it works on Python, JS/TS, Go, Java/Kotlin,
Ruby, PHP, Rust, C#, Elixir, Scala and Gherkin repos out of the box.

```console
$ gradebook-tests .
gradebook-tests 0.1.0 — /srv/checkout
languages: javascript (15)  ·  calibrated for javascript: 0.60x test:code, 2.0 cases/file
15 source files · 16 test files · 25 test cases · 25 assertions · 84 test lines / 39 source lines (2.15x)

  Coverage               ████████████████████  12.0/12  measured 91.3% (coverage/coverage-summary.json), gate 85%
  Mutation score         ····················   n/a/8   no mutation report found
  Unit tests             ██████████████████░░   7.9/9   13 file(s), 20 case(s) for 15 source files, 2.15x test:code lines (target 0.60x)
  Integration tests      ████████████░░░░░░░░   4.2/7   1 file(s), 2 case(s) (8% of all cases)
  Functional / E2E       █████████████████░░░   5.0/6   2 file(s), 3 case(s) (12% of all cases)
  Suite shape            █████████████████░░░   3.4/4   80/8/12 unit/integration/E2E — lopsided
  TDD discipline         ████████████████████   7.0/7   70% of 10 source commits also touched tests (1 test-only)
  Assertion quality      █████████████████░░░   6.0/7   1.0 assertions/case, 1 assert only truthy/not-null/snapshot
  Edge & failure paths   █████░░░░░░░░░░░░░░░   1.2/5   0/25 cases (0%) exercise a failure path, 6 (24%) touch a boundary value
  Risk targeting         ····················   n/a/5   no churn history to rank by
  Test substance         ███████████████████░   5.6/6   1 phantom symbol(s)
  Determinism & isolation ████████████████████   6.0/6   no clock, randomness, host or ordering dependencies
  Test focus             ████████████████████   5.0/5   cases are small, linear and focused
  Test naming            ████████████████░░░░   4.1/5   6.3 words/name, 68% describe behaviour, 68% state a condition, 2 placeholder
  Test doubles           ████████████████░░░░   4.7/6   3 double(s) in 2/25 cases (mocks), 1 assert only on the double
  Suite hygiene          ████████████████████   4.0/4   25 cases, no skips, no focused tests
  BDD / behaviour specs  ████████████████████   2.0/2   1 feature file(s), 2 Gherkin-style case(s)
  CI enforcement         ████████████████████   4.0/4   1 config(s): runs tests, collects coverage, matrix/strict flags

SCORE  86.5/100   grade A
not scored (weights redistributed): Mutation score, Risk targeting

Biggest wins:
  +3.8   Edge & failure paths — test what happens when things go wrong: invalid input, timeouts, denied permissions, missing records — aim for ~25% of cases
  +2.8   Integration tests — grow the integration layer — test real collaborators (db, queue, http) rather than mocks only
  +1.3   Test doubles — 1 case(s) only verify that a double was called — assert on the returned value or the resulting state instead

Red flags (1):
  tests/unit/notifier.test.js  phantom-symbol     imports `notify`, which no source file defines — dead or invented test
```

## Usage

```sh
pipx install ./gradebook-tests
gradebook-tests .                          # score the repo you are in
gradebook-tests ../other-repo              # score anything, no setup needed
gradebook-tests . --by-dir                 # score each subproject, worst first
gradebook-tests . --format markdown        # paste-ready PR comment
gradebook-tests . --format json            # tooling integration
gradebook-tests . --fail-under 60          # absolute CI gate
gradebook-tests . --no-git                 # skip the git-history analysis
gradebook-tests . --max-flags 10           # cap the red flags listed (default: all)
gradebook-tests . --list-dimensions        # the scoring model
```

The regression gate — the one most repos can actually switch on today — is in
[Gating CI](ci.md).

## The scoring model

| Dimension | Pts | What earns them |
|---|---:|---|
| Coverage | 12 | tooling wired up (0.25), a threshold that fails the build (0.20), and what a committed report *actually measures* (0.55, scaled to 85%). A declared threshold with no report is worth less than a measured number. |
| Mutation score | 8 | killed mutants from a Stryker, PIT or cargo-mutants report — the only direct evidence that the suite catches bugs. **Scored only when a report exists**, so nobody is punished for not running mutation testing. |
| Unit tests | 9 | three ratios of test to code: test files per source file (~1 per 2-3), cases per source file, and **test lines per source line** — the last two calibrated per language (see below). A repo can have a test file per module and still have written 20 lines of test against 2,000 lines of code. |
| Integration tests | 7 | a real integration layer — sized as a share of the whole suite and tempered by absolute count, so one token test does not max it out |
| Functional / E2E | 6 | the same, for journeys through the whole system |
| Suite shape | 4 | the pyramid's proportions rather than its parts: a broad unit base, a real integration band, a thin E2E tip. Catches the ice-cream cone, unit tests with no integration tests, and integration tests with no unit base. |
| TDD discipline | 7 | from `git log`: how often source commits also carry tests, test-only (red-step) commits, and how many **bugfix commits shipped a regression test** |
| Assertion quality | 7 | cases that assert nothing dominate, then cases whose every assertion is weak — `assertTrue`, `toBeTruthy`, `not-null`, bare `assert thing`, snapshot-only, `assert True` — then, in ecosystems whose frameworks do not print the compared values, assertions that report nothing on failure. Density matters least. |
| Edge & failure paths | 5 | the share of cases that exercise something going wrong — raised exceptions, timeouts, invalid input, missing records (~25%) — plus the share that touch a boundary value: empty, zero, negative, null, maximum (~20%). |
| Risk targeting | 5 | whether the files that change most often are the ones under test. Churn is the best available proxy for where the next bug lands, so an untested hotspot is named as a red flag with its change count. |
| Test substance | 6 | the low-effort tells: copy-pasted cases, assertions that cannot fail, imports of code that does not exist, tests frozen while their module churned, modules with a test file and almost no coverage, tests reaching into privates, and expectations recomputed from the inputs |
| Determinism & isolation | 6 | the tests that fail on someone else's machine: unfrozen clock reads, unseeded randomness, hard-coded hosts/paths/URLs, order-dependent naming and shared state, hard-coded sleeps, brittle positional/generated locators, and a suite pinned to a single worker |
| Test focus | 5 | one case, one behaviour: cases over 50 lines, cases with `if`/`switch` logic deciding what gets checked, cases with 10+ assertions, and oversized shared setup |
| Test naming | 5 | names that state a behaviour and a condition (`returns_404_when_the_user_is_missing`) rather than a subject (`testUserService`), nothing at all (`test_1`, `it('works')`), or the name of the method being called (`test_charge` for `charge()` — one test per method mirrors the code instead of describing it) |
| Test doubles | 6 | mocks, stubs and spies used at real seams — penalised for cases whose every assertion just checks that a double was called, for wiring many doubles per case, for a suite where almost nothing real runs, and for never resetting them |
| Suite hygiene | 4 | penalties for skipped/xfailed tests, `.only`/`fdescribe` left in, and no parametrised/table-driven tests |
| BDD / behaviour specs | 2 | Gherkin features and step definitions score above spec-style `describe`/`it`, which is mostly a naming convention |
| CI enforcement | 4 | CI runs the suite, collects coverage, and uses a matrix or strict flags |

The seventeen always-scored dimensions add up to 100; mutation score adds 8 more
when a report is there to read, and every weight renormalises around it.

Grades: **A** ≥85, **B** ≥70, **C** ≥55, **D** ≥40, **F** below.

A dimension that cannot be judged (no git history, no source files) is *not
scored* rather than scored zero, and the remaining weights are renormalised —
the report says which, so a missing signal never quietly inflates or sinks the
number.

## How tests are found and classified

- **Test files** — ecosystem naming conventions (`test_*.py`, `*_test.go`,
  `*.spec.ts`, `*Test.java`, `*_spec.rb`, `*Test.php`, `#[test]`, `*.feature`, …)
  plus anything of a known language under a `test/`, `spec/`, `__tests__/` or
  `features/` directory.
- **Layer** — directory names first (`unit/`, `integration/`, `e2e/`,
  `acceptance/`, `contract/`, `perf/`), then content: testcontainers, supertest,
  `@SpringBootTest` and live DB/HTTP clients say integration; playwright,
  cypress, selenium, capybara say E2E.
- **Cases and assertions** — counted per language, and every case is checked for
  at least one assertion in its own body.
- **Names** — extracted per language (`def test_*`, `it('...')`, `func Test*`,
  `t.Run("...")`, backticked Kotlin names, `Scenario:` lines, …), split into
  words, then judged: a name is *descriptive* when it carries three meaningful
  words, or two plus an expectation (`returns`, `raises`, `rejects`) or a
  condition (`when`, `given`, `without`); filler-only names (`test_1`,
  `it('works')`, `testFoo`) are called out by name in the advice.
- **Assertions** — a *weak* assertion accepts almost any value (`assertTrue`,
  `toBeTruthy`, `toBeDefined`, `assertNotNull`, a bare `assert thing`, a
  snapshot match, `assert True`). A case whose assertions are *all* weak runs
  the code without pinning behaviour down, and is counted apart from cases that
  assert nothing at all.
- **Failure paths** — a case counts when it asserts on an error
  (`pytest.raises`, `toThrow`, `assertThrows`, `require.Error`) or its name says
  so (`invalid`, `missing`, `timeout`, `rejects`, `expired`, `denied`).
- **Test doubles** — creation is detected across `unittest.mock`, `jest`/`vitest`,
  sinon, testdouble, Mockito, gomock, NSubstitute, Mockery, RSpec doubles, nock,
  WireMock and friends, attributed to the case that uses them (decorators and
  annotations included). A case whose assertions are *all* interaction checks
  (`assert_called_once_with`, `toHaveBeenCalled`, `verify(...)`) is counted as
  testing the double rather than the behaviour.
- **Coverage** — parses cobertura/`coverage.xml`, `lcov.info`, jacoco,
  istanbul `coverage-summary.json`, `coverage.json` and Go coverprofiles, and
  reads thresholds from `.coveragerc`, `pyproject.toml`, jest
  `coverageThreshold`, nyc, codecov and CI flags.

The ten red-flag detectors that feed *Test substance*, *Risk targeting* and
*Determinism & isolation* — and the anti-pattern catalogue behind them — are in
[Anti-patterns](anti-patterns.md).

## Calibrated per language

A single set of thresholds mis-scores most ecosystems, so the targets that
genuinely differ are weighted by how much of the repo each language is, and the
calibration is printed with the languages:

```
languages: go (22)  ·  calibrated for go: 0.80x test:code, 1.5 cases/file
```

| | Why it differs |
|---|---|
| **test:code line ratio** | Go tests are verbose — table-driven cases and explicit error checks — so 0.80x is the bar; pytest is terse, so 0.50x is. Java 0.90x, Rust 0.40x, shell 0.30x. |
| **cases per source file** | Go table-driven tests pack many cases into one function (1.5); RSpec spreads them out (2.5). |
| **bare assertions** | `assertTrue(x)` in JUnit tells you "expected true, got false" and nothing else — that is where Assertion Roulette comes from. pytest rewrites the assert and prints both operands, and jest prints the diff, so the same code is fine there. Checked for Java, Kotlin, C#, PHP, Node `assert`, and Go's `t.Fatal("boom")` with no values; **not** for pytest, jest or RSpec. |
| **spec-style BDD** | `describe`/`it` is a weak Gherkin substitute in most stacks, but it *is* the ecosystem's idiom in RSpec and Jasmine — so its ceiling is 0.8 there and 0.55 elsewhere. |

An ecosystem-specific check only applies when that ecosystem is at least half
the repo, so a stray Java file in a Python codebase does not start scoring the
Python tests by JUnit's rules. Unknown languages fall back to the neutral
profile rather than being guessed at.

## Caveats

Heuristics, not semantics: it counts and classifies, it does not run your
tests. Double detection is name-based, so a hand-rolled fake with no library
behind it reads as "no doubles", and a test that asserts on a value the double
was told to return still looks honest. Red flags are conservative by design —
duplicates need three matches, phantoms only count project-relative imports —
so read them as leads, not verdicts.

A tool that greps for test code will flag its own test fixtures:
`gradebook-tests` scores its own suite as having a skipped test, because one of
its fixtures contains the string `@pytest.mark.skip`. Generated test files
inflate counts, a repo that tests through a custom harness will under-count, and
vendored or build directories are skipped rather than analysed.

Treat the number as a conversation starter and the "biggest wins" list as the
actual output.
