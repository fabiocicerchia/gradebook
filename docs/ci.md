# Gating CI

## The trend, not the number

Most repos cannot clear an absolute bar on day one, so the useful gate is *do
not get worse*:

```sh
gradebook-tests . --format json > baseline.json          # commit this, or cache it
gradebook-tests . --baseline baseline.json --fail-on-drop
gradebook-tests . --baseline baseline.json --fail-on-drop 2   # allow 2 points of slack
```

The report then shows a Δ column per dimension and the total against the
baseline, so a red build points at the dimension that moved. If the baseline
scored a different set of dimensions — say it was taken with `--no-git`, or
before a mutation report existed — the totals are not directly comparable and
the report says so rather than pretending otherwise.

Both tools take the same flags, so the code half is identical:

```sh
gradebook-code . --format json > code-baseline.json
gradebook-code . --baseline code-baseline.json --fail-on-drop
```

## The absolute bar

For a repo that already clears one:

```sh
gradebook-tests . --fail-under 60
gradebook-code . --fail-under 60
```

Either gate exits non-zero when it fails, so it works as a CI step with no
wrapper.

## As a PR comment

`--format markdown` produces a paste-ready table; `--format json` is the stable
shape `--baseline` reads.

```yaml
- run: pipx install ./gradebook-code
- run: gradebook-code . --format markdown >> "$GITHUB_STEP_SUMMARY"
- run: gradebook-code . --baseline code-baseline.json --fail-on-drop
```

## Monorepos

`--by-dir` scores every immediate subdirectory that holds code of its own and
ranks them worst-first, because one repo-wide number hides the module that
needs the work:

```console
$ gradebook-tests . --by-dir
...
By directory (worst first):
  F    1.6  k8s-ai-sec   98 src / 2 test      → wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it
  D   43.7  tm_delta     8 src / 1 test       → wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it
  C   61.5  tools        19 src / 27 test     → wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it
```
