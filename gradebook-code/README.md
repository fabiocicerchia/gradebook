# gradebook-code

**Is this code worth testing?**

`gradebook-code` walks any repository and scores it **0-100** against the
principles people argue about in review but rarely measure: DRY, YAGNI, GRASP,
SOLID and KISS. Thirteen weighted dimensions, letter-graded A–F, each one backed
by red flags with a `file:line` — so the output is a list of files to open, not
a number to feel bad about.

No config, no build, no test run: a read-only pass over the working tree plus
`git log`, standard library only. Works across Python, JS/TS, Go, Java/Kotlin,
Ruby, PHP, Rust, C#, Elixir, Scala and more.

```sh
pipx install ./gradebook-code

gradebook-code .                       # score the repo you are in
gradebook-code ../other-repo           # score anything, no setup needed
gradebook-code . --by-dir              # per subproject, worst first
gradebook-code . --format markdown     # paste-ready PR comment
gradebook-code . --list-dimensions     # the scoring model
gradebook-code . --fail-under 60       # absolute CI gate

# regression gate — fail when the code gets worse, not when it is imperfect
gradebook-code . --format json > baseline.json
gradebook-code . --baseline baseline.json --fail-on-drop
```

A dimension with no evidence — no interfaces, no inheritance, no git history —
is **not scored** rather than scored zero, and the remaining weights
renormalise. Thresholds are calibrated per language. Generated and minified
files are skipped rather than scored, and the header says how many.

**A low score is an argument, not a verdict.** Generated code, an interpreter
loop, a parser table and a state machine all score badly for good reasons. Read
the flags before you believe the number.

Full documentation, the dimension-by-dimension model, and the sibling tool
`gradebook-tests` (which scores the suite that covers this code):
<https://github.com/fabiocicerchia/gradebook>

## License

Apache 2.0 — see [LICENSE](LICENSE).
