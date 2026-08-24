# Status & roadmap

## gradebook-tests

- [x] Seventeen always-scored dimensions (+ mutation score when a report
      exists), renormalised when a signal is unavailable
- [x] Multi-ecosystem discovery, layer classification, coverage report parsing
- [x] Git-history TDD signal, text/JSON/Markdown output, `--fail-under` gate
- [x] Test-name readability and test-double discipline, with named offenders
- [x] Weak-assertion and failure-path analysis
- [x] Mutation reports (Stryker, PIT, cargo-mutants) as a first-class dimension
- [x] `--baseline` regression gate and `--by-dir` monorepo breakdown
- [x] Red flags with file:line — duplicates, suppressed failures, phantom
      imports, stale tests, decorative test files, private access, brittle
      locators, mirrored expectations
- [x] Suite shape, determinism/isolation and test focus dimensions from the
      testing anti-pattern literature
- [ ] Per-repo config (`.gradebook-tests.toml`: weights, ignores, custom test
      globs, overriding the language profile)
- [ ] mutmut report support (its cache is sqlite, not a file we can read yet)
- [ ] Flakiness signal from CI history (re-run rates per test), which is the
      only honest way to score flakiness
- [ ] Test runtime from JUnit XML, so slow tests stop being invisible
- [ ] Detect assertions on values that were themselves stubbed (full tautologies)
- [ ] Phantom-symbol checking for Go, Java and Ruby (needs symbol resolution,
      not just import names)
- [ ] GitHub Action wrapper

## gradebook-code

- [x] Thirteen weighted principle dimensions, renormalised when evidence is
      absent
- [x] Per-language calibration, red flags with file:line, `--by-dir`
- [x] `--fail-under` and `--baseline` regression gates, text/JSON/Markdown
- [x] Cross-language comment/string scanner, validated against Python's `ast`
- [x] Churn-weighted hotspots from `git log`
- [ ] Real call-graph fan-in/fan-out instead of import edges
- [ ] Per-repo config (`.gradebook-code.toml`: weights, ignores, thresholds)
- [ ] Fan-in and instability (`I = Ce/(Ca+Ce)`) from the import graph already
      built
