# gradebook-tests

**Is this suite worth anything?**

Coverage percentage tells you which lines ran, not whether your suite would
catch a regression. `gradebook-tests` walks any repository, finds and classifies
its tests (unit, integration, functional/E2E, BDD), reads whatever coverage
evidence actually exists, mines git history for TDD discipline, judges whether
test names describe behaviour, tells a real assertion from one that accepts
anything, checks whether mocks and stubs sit at real seams, hunts down the tests
written to satisfy a checkbox, and grades it **0-100** — then tells you which
fix buys the most points and which files to open first.

No config, no language server, no test run: a read-only pass over the working
tree plus `git log`, standard library only. Works on Python, JS/TS, Go,
Java/Kotlin, Ruby, PHP, Rust, C#, Elixir, Scala and Gherkin repos out of the
box.

```sh
pipx install ./gradebook-tests

gradebook-tests .                       # score the repo you are in
gradebook-tests . --by-dir              # per subproject, worst first
gradebook-tests . --format markdown     # paste-ready PR comment
gradebook-tests . --list-dimensions     # the scoring model
gradebook-tests . --fail-under 60       # absolute CI gate

# regression gate — fail when the suite gets worse, not when it is imperfect
gradebook-tests . --format json > baseline.json
gradebook-tests . --baseline baseline.json --fail-on-drop
```

Eighteen weighted dimensions adding to 100, letter-graded A–F. A dimension with
no evidence is **not scored** rather than scored zero, and the remaining weights
renormalise — the report names every one it dropped. Thresholds are calibrated
per language: a 47-line function is unremarkable in Go and too long in Python.

Every red flag carries a `file:line`. The score is the headline; the flags are
the product.

Full documentation, the dimension-by-dimension model, and the sibling tool
`gradebook-code` (which scores the code the suite covers):
<https://github.com/fabiocicerchia/gradebook>

## License

Apache 2.0 — see [LICENSE](LICENSE).
