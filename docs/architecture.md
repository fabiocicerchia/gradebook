# Architecture

Two independent programs in sibling folders, sharing docs, a Makefile and a CI
job — and nothing else. `gradebook-tests` scores the test suite; `gradebook-code`
scores the code it covers.

## Overview

Both are a **read-only pass over the working tree** plus `git log`. No config
file, no build, no test run, no language server, no network. That constraint is
what lets either one be pointed at a repository it has never seen — including
one in a language its author does not write — and produce a number in seconds.

```text
repo path ──► discover files ──► detect & weight languages ──► calibrate thresholds
                                                                      │
                        ┌─────────────────────────────────────────────┘
                        ▼
             per-dimension analysers ──► scores + red flags (file:line)
                        │
                        ▼
      renormalise over dimensions with evidence ──► 0-100, letter grade
                        │
                        ▼
             text | json | markdown   (+ --by-dir, --fail-under, --baseline)
```

## Components

| Path                                 | Responsibility                                                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `gradebook-tests/gradebook_tests.py` | the whole suite scorer: discovery, classification, coverage evidence, git-history TDD signals, assertion and naming analysis, test smells |
| `gradebook-code/gradebook_code.py`   | the whole code scorer: complexity, duplication, coupling/cohesion, SOLID heuristics, churn-weighted hotspots                              |
| `gradebook-*/tests/`                 | pytest suites, one per tool                                                                                                               |
| `Makefile`                           | one entry point over two folders — each still builds, tests and lints alone                                                               |

Each tool is a single module with a console-script entry point. They do not
import each other, and neither has a runtime dependency outside the standard
library.

## Data flow

1. **Discover.** Walk the tree, skipping generated and minified files
   (`*.pb.go`, `*_pb2.py`, `*.min.js`, `@generated`, `DO NOT EDIT`). The header
   line reports how many were skipped — they are not silently scored as zero.
1. **Calibrate.** Detect the languages present and weight thresholds by how much
   of the repo each one is. A 47-line function is unremarkable in Go and too
   long in Python.
1. **Score each dimension.** `gradebook-tests` has 18 (Coverage 12 pts down to
   BDD 2); `gradebook-code` has 13 (Simplicity 13 pts down to Liskov 5). Weights
   add to 100.
1. **Renormalise.** A dimension with **no evidence** — no git history, no
   interfaces, no inheritance — is *not scored* rather than scored zero, and the
   remaining weights are redistributed. The report names every one it dropped.
1. **Report.** Score, letter grade (A ≥85, B ≥70, C ≥55, D ≥40, F below), the
   dimension table, and red flags ranked by severity with `file:line`.

## Decisions

- **Two programs, not one with a flag.** They answer different questions and are
  useful separately; a repo may want one gate and not the other. Sharing a
  folder is documentation, not coupling.
- **No evidence ≠ zero.** Scoring an absent signal as zero punishes a repo for
  what it does not have and quietly sinks the number. Dropping the dimension and
  saying so is the honest arithmetic.
- **Stdlib only.** The tools grade other people's repos; an install that drags
  in a dependency tree is a tool nobody runs on a whim.
- **`file:line` or it didn't happen.** A score is not actionable. The red flags
  are the product; the number is the headline.
- **Regression gates over absolute bars.** `--baseline` + `--fail-on-drop` is
  the gate a real repo can switch on today; `--fail-under N` is for the ones
  that already clear the bar.
- **A low score is an argument, not a verdict.** A parser table, an interpreter
  loop and a state machine all score badly for good reasons.
