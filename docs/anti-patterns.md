# Anti-patterns and red flags

A score does not help a junior, and it does not help you review a pull request
full of generated tests. The **red flags** section names files and lines:

```console
$ gradebook-tests ../legacy-billing
  CI enforcement         ░░░░░░░░░░░░░░░░░░░░   0.0/5   no CI configuration found

SCORE  32.2/100   grade F
not scored (weights redistributed): Mutation score, TDD discipline

Red flags (6):
  tests/test_billing.py     phantom-symbol     imports `calculate_discount`, which no source file defines — dead or invented test
  tests/test_billing.py:20  suppressed-failure assertion commented out
  tests/test_billing.py:28  suppressed-failure failure swallowed by an empty except/catch
  tests/test_billing.py:32  suppressed-failure test skipped with no reason given
  tests/test_billing.py:9   duplicate-case     same body as tests/test_billing.py:4 — parametrise instead
  tests/test_billing.py:14  duplicate-case     same body as tests/test_billing.py:4 — parametrise instead
```

## The ten detectors

All reported with a location, feeding the *Test substance*, *Risk targeting*
and *Determinism & isolation* dimensions of
[gradebook-tests](gradebook-tests.md):

- **duplicate-case** — three or more cases whose bodies are identical once
  names, comments and literals are stripped. Two matching bodies are common and
  often fine; three is a copy-paste run that tests one path repeatedly and
  should be one parametrised case.
- **suppressed-failure** — assertions that cannot fail: commented out, wrapped
  in an empty `except`/`catch`, behind `if False`, or a test skipped with no
  reason given.
- **phantom-symbol** — a test importing project code that no source file
  defines. Those tests have never run against this repo; they are dead, or they
  were invented. Checked for Python and JS/TS, where imports name what they
  pull in, and only against project-relative imports.
- **stale-test** — a test file that has not changed while the module it covers
  changed five or more times. It no longer describes the code.
- **decorative-test** — a module that *has* a test file and is still under 40%
  covered, from per-file coverage data. The test exists; it exercises nearly
  nothing.
- **implementation-access** — a test reaching into `._private`, `#private`,
  `__dict__` or reflection. The next refactor breaks the test without breaking
  the code.
- **mirror-assertion** — the expected value is recomputed from the inputs
  (`assert total(cart) == sum(i.price for i in cart)`). The test shares the
  formula it is meant to check, so a wrong formula passes. Calls that only
  reshape a literal (`sorted`, `len`, `pytest.approx`, …) are not counted.
- **untested-hotspot** — a source file among the most-changed in the repo with
  no test file at all, named with its change count. "Write tests for code that
  breaks often, changes often, is critical to the business."
- **conjoined-twin** — a file filed under `unit/` that imports testcontainers,
  a real HTTP client or a browser driver. It is an integration test wearing a
  unit test's badge, and it makes the fast suite slow and the shape dishonest.
- **brittle-selector** — positional XPath, `nth-child`, generated class names
  (`.css-1a2b3c`): the record-and-playback signature, and the usual reason a UI
  suite is flaky. Suppressed when the same file also uses roles, labels or
  `data-testid`, since that file has clearly made the choice deliberately.

`gradebook-code` has its own flag set — `hotspot`, `god-file`,
`complex-function`, `dependency-cycle` and the rest — listed in
[gradebook-code](gradebook-code.md#red-flags).

## The catalogue behind the scoring model

The scoring model is a catalogue of testing anti-patterns turned into things a
static pass can actually see. What each one maps to:

| Anti-pattern                                                        | Where it shows up                                  |
| ------------------------------------------------------------------- | -------------------------------------------------- |
| Ice-cream cone / inverted pyramid                                   | Suite shape                                        |
| Unit tests without integration tests                                | Suite shape, Integration tests                     |
| Integration tests without a unit base                               | Suite shape, Unit tests                            |
| The Liar (passes without testing what it claims)                    | Assertion quality, Test doubles                    |
| The Mockery / over-mocking                                          | Test doubles                                       |
| Testing the mock instead of the code                                | Test doubles (interaction-only cases)              |
| The Inspector / Anal Probe (reaching into privates)                 | Test substance (`implementation-access`)           |
| The Ugly Mirror / Doppelgänger (test recomputes the expected value) | Test substance (`mirror-assertion`)                |
| Line Hitter (executes code, analyses no output)                     | Assertion quality (cases that assert nothing)      |
| Brittle locators / record-and-playback output                       | Determinism & isolation (`brittle-selector`)       |
| Assertion Roulette / The Giant / Eager Test                         | Test focus                                         |
| Conditional test logic                                              | Test focus                                         |
| Excessive setup (Mother Hen)                                        | Test focus                                         |
| The Enumerator (`test1`, `test2`)                                   | Test naming                                        |
| The Butterfly (unfrozen clocks, randomness)                         | Determinism & isolation                            |
| The Local Hero / Resource Optimism (hosts, paths, URLs)             | Determinism & isolation                            |
| Chain Gang / Generous Leftovers (order dependence, shared state)    | Determinism & isolation                            |
| Wait-and-see (hard-coded sleeps)                                    | Determinism & isolation                            |
| The Free Ride / copy-paste tests                                    | Test substance (`duplicate-case`)                  |
| The Secret Catcher / swallowed failures                             | Test substance (`suppressed-failure`)              |
| Second-class citizen test code                                      | Test substance, Test focus                         |
| Happy Path / Liar / Success Against All Odds                        | Edge & failure paths                               |
| Never testing boundaries or equivalence partitions                  | Edge & failure paths                               |
| Tests that cannot run in parallel or in any order                   | Determinism & isolation                            |
| Not converting bugs into regression tests                           | TDD discipline (bugfix commits without tests)      |
| Testing the wrong functionality (not what breaks often)             | Risk targeting (`untested-hotspot`)                |
| Conjoined Twins (unit tests that are really integration tests)      | Test substance (`conjoined-twin`)                  |
| Test-per-Method (one test per production method)                    | Test naming                                        |
| The Loudmouth (console chatter instead of assertions)               | Suite hygiene                                      |
| The Greedy Catcher (failure logged, test passes)                    | Test substance (`suppressed-failure`)              |
| Operating System Evangelist (platform branches)                     | Determinism & isolation                            |
| Mocking everything with no integration layer behind it              | Test doubles                                       |
| Coverage as the goal (Goodhart)                                     | Mutation score, Test substance (`decorative-test`) |
| Manual testing only / not in CI                                     | CI enforcement                                     |
| Skipped tests left to rot                                           | Suite hygiene, Test substance                      |

## Sources

Read in full rather than summarised from memory:

- [Kostis Kapelonis, *Software Testing Anti-patterns*](https://blog.codepipes.com/testing/software-testing-antipatterns.html) (13 anti-patterns)
- [Yegor Bugayenko, *Unit Testing Anti-Patterns: Full List*](https://www.yegor256.com/2018/12/11/unit-testing-anti-patterns.html)
  — the [James Carr](http://agileinaflash.blogspot.com/2009/06/tdd-antipatterns.html)
  catalogue plus Line Hitter, Cuckoo, Test-per-Method, Conjoined Twins and
  Forty-Foot Pole
- [testRigor, *Software Testing Anti-Patterns and Ways To Avoid Them*](https://testrigor.com/blog/anti-patterns-in-software-testing/)
- [Enov8, *Software Testing Anti Patterns*](https://www.enov8.com/blog/software-testing-anti-patterns/)
- [Stephan Schmidt, *Mocking is an Anti-Pattern*](https://www.amazingcto.com/mocking-is-an-antipattern-how-to-test-without-mocking/)
- the xUnit Test Patterns smells, and the UI-automation literature on brittle
  selectors and record-and-playback

## Deliberately not guessed at

**Not detectable without running the suite:** slow tests, genuinely flaky tests
(only their static predictors are scored), whether a test would have caught the
bug it claims to cover, testing the wrong functionality, and whether TDD was
actually practised rather than reconstructed from commit shape.
