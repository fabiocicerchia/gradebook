# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated from Conventional Commit messages by release-please — don't edit it
by hand. `version.txt` tracks the repo; each package keeps its own version in
its `pyproject.toml`, and the two are bumped together.

## [0.3.0](https://github.com/fabiocicerchia/gradebook/compare/v0.2.1...v0.3.0) (2026-09-01)


### Features

* add editor extensions and list every red flag by default ([#9](https://github.com/fabiocicerchia/gradebook/issues/9)) ([b827ed3](https://github.com/fabiocicerchia/gradebook/commit/b827ed3b21a88ef0bd84e5bc51dff2843592d35a))

## [0.2.1](https://github.com/fabiocicerchia/gradebook/compare/v0.2.0...v0.2.1) (2026-08-29)


### Bug Fixes

* **docs:** hash-pin the docs toolchain and require hashes on install ([#10](https://github.com/fabiocicerchia/gradebook/issues/10)) ([37c9816](https://github.com/fabiocicerchia/gradebook/commit/37c9816abba229a4578c1af5c742e63d1d9c66ed))

## [0.2.0](https://github.com/fabiocicerchia/gradebook/compare/v0.1.0...v0.2.0) (2026-08-25)


### Features

* **docs:** build the docs site in Actions and drop Read the Docs ([#7](https://github.com/fabiocicerchia/gradebook/issues/7)) ([003f573](https://github.com/fabiocicerchia/gradebook/commit/003f573b17780753b9eef4f5875f3e585b703568))

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
