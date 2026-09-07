# gradebook-code — is this code worth testing?

The other half of the pair: `gradebook-tests` grades the tests, this grades the
code they cover. **DRY, YAGNI, GRASP, SOLID and KISS** are famous, and arguing
about them is a hobby — so `gradebook-code` scores their *observable
consequences*: how complex the functions are, how much is copy-pasted, how wide
the classes are, how far the dependencies reach, how much abstraction exists for
a single caller.

No config, no build, no type checker: a read-only pass over the working tree
(plus `git log`), across Python, JS/TS, Go, Java/Kotlin, Ruby, PHP, Rust, C#,
Elixir, Scala, Swift, C/C++, Lua and shell.

Every metric is read from source with comments and string contents blanked
first, so a docstring saying *"if the kind is a circle, for squares, while you
are at it"* no longer adds four branches to a function that has none, and a
`"}"` inside a string no longer ends a function early. The blanking preserves
offsets, so reported line numbers still point at the right line. This is done
the same way for all fifteen languages rather than only where a parser happens
to exist — and the numbers are checked against Python's `ast` in the test suite,
on the one language where an oracle is available.

```console
$ gradebook-code .
gradebook-code 0.1.0 — /srv/mockterview
languages: go (22)  ·  calibrated for go: 60 lines, complexity 12, 5 params
22 files · 2,087 lines · 100 functions · 41 classes · 22 modules

  Simplicity (KISS)              ████████████████████  13.7/14  3.9 average complexity over 100 functions, 1 over complexity 12
  Duplication (DRY)              ████████████████████  12.0/12  0.0% of lines duplicated elsewhere
  Single responsibility          ████████████████████  10.0/10  no god files, no class doing three jobs
  Open/closed                    ████████████████████   8.0/8   no type-branching found
  Liskov substitution            ████████████████████   5.0/5   41 subclass(es)
  Interface segregation          ████████████████████   6.0/6   5 interface(s), none oversized
  Dependency inversion           ████████████████░░░░   6.5/8   9% of files touch a database, HTTP client or filesystem directly
  Coupling (GRASP)               ████████████████████   9.8/10  0.4 internal imports per module
  Cohesion (GRASP)               ····················   n/a/7   no classes with shared state to judge
  Law of Demeter                 ███████████████████░   4.8/5   2 chains of 3+ dots (0.1 per 100 lines)
  Speculative generality (YAGNI) ████████████████████   8.8/9   4 block(s) of commented-out code
  Naming & intent                █████████████░░░░░░░   4.0/6   7/141 vague names (manager, helper, data, process, …)

SCORE  95.4/100   grade A
not scored (weights redistributed): Cohesion (GRASP)

Biggest wins:
  +2.0   Naming & intent — name things for what they are: a Manager or a Helper is a class nobody could describe, and a boolean parameter hides two functions
  +1.5   Dependency inversion — concentrate infrastructure behind a few adapters and inject it, so the rules can be read and tested without a database

Red flags (1):
  internal/tui/update.go:12  complex-function   `Update` has 13 complexity (limit 12)
```

## Usage

```sh
pipx install ./gradebook-code
gradebook-code .                          # score the repo you are in
gradebook-code ../other-repo              # score anything, no setup needed
gradebook-code . --by-dir                 # score each subproject, worst first
gradebook-code . --format markdown        # paste-ready PR comment
gradebook-code . --format json            # tooling integration
gradebook-code . --fail-under 60          # absolute CI gate
gradebook-code . --max-flags 10           # cap the red flags listed (default: all)
gradebook-code . --list-dimensions        # the scoring model
```

The regression gate is in [Gating CI](ci.md).

## The scoring model

| Principle                      | Pts | What is measured                                                                                                                                                                                                          |
| ------------------------------ | --: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Simplicity (KISS)              | 13  | cyclomatic complexity, function length, nesting depth and parameter count per function, against per-language limits                                                                                                       |
| Duplication (DRY)              | 11  | windows of 8+ consecutive statement lines that appear verbatim elsewhere (identifiers kept, literals masked), plus magic literals repeated across the codebase                                                            |
| Single responsibility          | 9   | god files (400+ lines or 20+ functions), files mixing three or more concerns (database, HTTP, filesystem, UI, crypto, queue), classes past 15 methods                                                                     |
| Coupling (GRASP)               | 9   | import cycles between the repo's own modules, and average internal fan-out                                                                                                                                                |
| Open/closed                    | 8   | branching on a `type`/`kind`/`status` field, and runtime type checks (`isinstance`, `instanceof`, `reflect.TypeOf`) — every new case editing the same three functions                                                     |
| Dependency inversion           | 8   | how far infrastructure has spread: the share of files reaching a database driver, HTTP client or filesystem directly, plus mutable global state                                                                           |
| Speculative generality (YAGNI) | 8   | private symbols nothing references, abstractions with exactly one implementer, unimplemented stubs, commented-out code, TODO/FIXME markers                                                                                |
| Cohesion (GRASP)               | 7   | the share of a class's methods that touch its own fields. **Scored only where classes hold state.**                                                                                                                       |
| Hotspots (churn × complexity)  | 6   | complexity weighted by how often the file actually changes, from `git log`. Complexity in a file nobody touches is a fact; complexity in one that changes weekly is a bill. **Scored only where there is churn history.** |
| Interface segregation          | 6   | interfaces, protocols, traits and abstract classes declaring 8+ methods. **Scored only where interfaces exist.**                                                                                                          |
| Liskov substitution            | 5   | overrides that raise `NotImplementedError`, and type checks around a hierarchy. **Scored only where inheritance exists.**                                                                                                 |
| Law of Demeter                 | 5   | `a.b.c.d` chains per 100 lines — reaching through objects you do not own                                                                                                                                                  |
| Naming & intent                | 5   | vague names (`data`, `process`, `Manager`, `Helper`, `util`) and boolean flag parameters, which hide two functions in one                                                                                                 |

The thirteen dimensions add up to 100. Grades: **A** ≥85, **B** ≥70, **C** ≥55,
**D** ≥40, **F** below.

A dimension with no evidence — no interfaces, no inheritance, fewer than three
modules, no stateful classes — is **not scored** rather than scored zero, and
the remaining weights renormalise. The report says which, so a missing signal
never quietly inflates or sinks the number.

## Calibrated per language

Thresholds are weighted by how much of the codebase each language is, and the
calibration is printed with the languages:

```text
languages: go (22)  ·  calibrated for go: 60 lines, complexity 12, 5 params
```

Go functions carry explicit error handling and Java carries ceremony, so they
get more room; Ruby and Elixir are terse and are held to less. A 47-line
function is unremarkable in Go and too long in Python, and `gradebook-code` says
so rather than applying one number to both.

## Red flags

The score says how bad; the flags say where. Every finding carries a file and
a line, ordered by how much they matter:

`hotspot` · `dependency-cycle` · `god-file` · `complex-function` ·
`duplicate-block` · `deep-nesting` · `mixed-concerns` · `fat-interface` ·
`dead-code` · `long-function` · `many-parameters`

```text
src/billing.py:1  hotspot  changed 8 times and carries 25 complexity
                           (codebase average 7) — the expensive kind
```

## Caveats

Regex and structure, not semantics: there is no AST, no type resolution and no
call graph, so everything here is a proxy for the principle rather than proof
of it. The consequences are worth knowing:

- **Liskov and Dependency inversion are the weakest.** Real LSP violations need
  behavioural analysis; `gradebook-code` sees unimplemented overrides and type
  checks. Real DIP is about which way the arrows point; it sees how widely
  infrastructure is imported.
- **Duplication is line-based.** It finds copy-paste, not two functions that do
  the same thing in different words.
- **Dead code is only detected for private symbols** — anything exported might
  have a caller outside the repo, so it is left alone.
- **Generated and minified files are skipped, not scored.** `*.pb.go`,
  `*_pb2.py`, `*.min.js`, and anything whose header says `@generated` or
  `DO NOT EDIT`. Nobody maintains them, and they would sink a score for no
  reason. The header line says how many were skipped.
- **A low score is an argument, not a verdict.** Generated code, an interpreter
  loop, a parser table and a state machine all score badly for good reasons.
  Read the flags before you believe the number.

Dogfooding, in that spirit — `gradebook-code` on its sibling:

```console
$ gradebook-code ./gradebook-tests
SCORE  53.0/100   grade D
not scored (weights redistributed): Hotspots (churn x complexity), Liskov substitution,
                                    Interface segregation, Coupling (GRASP), Cohesion (GRASP)
Red flags (46):
  gradebook_tests.py:1  god-file  2277 lines, 72 functions, 0 classes — more than one reason to change
```

One 2,277-line file with 16 functions past the complexity limit. It is right.
