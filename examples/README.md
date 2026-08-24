# Examples

Both tools take a path and need no setup, so the example is the repo in front of
you. Start with this one — it dogfoods honestly:

```sh
make dev

gradebook-tests .        # scores this repo's own two pytest suites
gradebook-code .         # scores the two modules they cover
```

`gradebook-code` rates `gradebook-tests` a **D**, mostly for being one 2,500-line file
with a long branching function in it. It is right, and that is the point: read
the red flags, not the number.

A paste-ready PR comment:

```sh
gradebook-code . --format markdown
```

The regression gate, which is what you would actually put in CI:

```sh
gradebook-code . --format json > baseline.json     # once, on the default branch
gradebook-code . --baseline baseline.json --fail-on-drop
```

Point either at anything else — `gradebook-tests ../some-other-repo` — including a
language you do not write. See [Getting Started](../docs/getting-started.md).
