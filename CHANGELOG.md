# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated from Conventional Commit messages by release-please — don't edit it
by hand. `version.txt` tracks the repo; each package keeps its own version in
its `pyproject.toml`, and the two are bumped together.

## [0.1.0](https://github.com/fabiocicerchia/gradebook/compare/v0.1.0...v0.1.0) (2026-08-24)


### Features

* grade a repository's tests and code against a weighted rubric ([82222f2](https://github.com/fabiocicerchia/gradebook/commit/82222f2d14721d7c6250fbd621e118f7d1df892e))

## [Unreleased]

### Added
- `gradebook-tests` — scores a repository's test suite 0-100 across classification,
  coverage evidence, TDD discipline, naming, assertion quality, mock placement
  and test smells.
- `gradebook-code` — scores the code itself against twelve weighted principle
  dimensions (DRY, YAGNI, GRASP, SOLID, KISS).

[Unreleased]: https://github.com/fabiocicerchia/gradebook/commits/main
