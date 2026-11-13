# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated from Conventional Commit messages by release-please — don't edit it
by hand. `version.txt` tracks the repo; each package keeps its own version in
its `pyproject.toml`, and the two are bumped together.

## [0.4.3](https://github.com/fabiocicerchia/gradebook/compare/v0.4.2...v0.4.3) (2026-11-13)


### Bug Fixes

* 2 issues found by code-atlas (end-of-life runtimes) ([#86](https://github.com/fabiocicerchia/gradebook/issues/86)) ([06a1214](https://github.com/fabiocicerchia/gradebook/commit/06a1214ff0cfa9aea03e3547ea21a4e07dad24c0))
* 2 issues found by code-atlas (silenced checks) ([#87](https://github.com/fabiocicerchia/gradebook/issues/87)) ([d3a1e64](https://github.com/fabiocicerchia/gradebook/commit/d3a1e6438bfc9df030244b6e9a2d0cada17d35b3))
* 3 issues found by code-atlas (ci that cannot fail) ([#85](https://github.com/fabiocicerchia/gradebook/issues/85)) ([ffc0165](https://github.com/fabiocicerchia/gradebook/commit/ffc01656032f6529cd45db8314b9a4e310ee4c14))
* 7 issues found by code-atlas (quality gates) ([#84](https://github.com/fabiocicerchia/gradebook/issues/84)) ([ab36710](https://github.com/fabiocicerchia/gradebook/commit/ab36710754ebf29a138c90281b7192958a4b7223))
* 8 issues found by code-atlas (code design) ([#88](https://github.com/fabiocicerchia/gradebook/issues/88)) ([716df63](https://github.com/fabiocicerchia/gradebook/commit/716df6394582f746f05b9019bfd2b972d3bf01fa))
* 9 issues found by code-atlas (test suites) ([#89](https://github.com/fabiocicerchia/gradebook/issues/89)) ([b3edf90](https://github.com/fabiocicerchia/gradebook/commit/b3edf90e86579986f431f14f96a3804fe086b9e0))

## [0.4.2](https://github.com/fabiocicerchia/gradebook/compare/v0.4.1...v0.4.2) (2026-09-20)


### Bug Fixes

* **ci:** keep actions: read on the job that uploads sarif ([#58](https://github.com/fabiocicerchia/gradebook/issues/58)) ([bfe4728](https://github.com/fabiocicerchia/gradebook/commit/bfe4728ef90618ae3d699dff56a7c1803724ef86))
* replace install and checkout instructions that cannot work ([#52](https://github.com/fabiocicerchia/gradebook/issues/52)) ([656a90f](https://github.com/fabiocicerchia/gradebook/commit/656a90f8289870d194e4b02ed2753773de42f4a7))
* stop the module VERSION constants drifting from the release ([#51](https://github.com/fabiocicerchia/gradebook/issues/51)) ([5f8344f](https://github.com/fabiocicerchia/gradebook/commit/5f8344fb165f4973989a826b90177652d1695838))

## [0.4.1](https://github.com/fabiocicerchia/gradebook/compare/v0.4.0...v0.4.1) (2026-09-16)


### Bug Fixes

* **vscode:** let an installed package outrank the open workspace ([#48](https://github.com/fabiocicerchia/gradebook/issues/48)) ([54ab889](https://github.com/fabiocicerchia/gradebook/commit/54ab889c65fcde1d00af9be28bcc757cae95c600))

## [0.4.0](https://github.com/fabiocicerchia/gradebook/compare/v0.3.0...v0.4.0) (2026-09-10)


### Features

* **packaging:** ship a man page with each wheel ([#34](https://github.com/fabiocicerchia/gradebook/issues/34)) ([25bad7d](https://github.com/fabiocicerchia/gradebook/commit/25bad7d16d4778b93d253f96363f526b1f4b29cc))


### Bug Fixes

* **ci:** pin the editorconfig-checker binary version ([#23](https://github.com/fabiocicerchia/gradebook/issues/23)) ([c2212ab](https://github.com/fabiocicerchia/gradebook/commit/c2212abd9b28ee323b550c5563f160f52178a79d))

## [0.3.0](https://github.com/fabiocicerchia/gradebook/compare/v0.2.1...v0.3.0) (2026-09-01)

### Features

- add editor extensions and list every red flag by default ([#9](https://github.com/fabiocicerchia/gradebook/issues/9)) ([b827ed3](https://github.com/fabiocicerchia/gradebook/commit/b827ed3b21a88ef0bd84e5bc51dff2843592d35a))

## [0.2.1](https://github.com/fabiocicerchia/gradebook/compare/v0.2.0...v0.2.1) (2026-08-29)

### Bug Fixes

- **docs:** hash-pin the docs toolchain and require hashes on install ([#10](https://github.com/fabiocicerchia/gradebook/issues/10)) ([37c9816](https://github.com/fabiocicerchia/gradebook/commit/37c9816abba229a4578c1af5c742e63d1d9c66ed))

## [0.2.0](https://github.com/fabiocicerchia/gradebook/compare/v0.1.0...v0.2.0) (2026-08-25)

### Features

- **docs:** build the docs site in Actions and drop Read the Docs ([#7](https://github.com/fabiocicerchia/gradebook/issues/7)) ([003f573](https://github.com/fabiocicerchia/gradebook/commit/003f573b17780753b9eef4f5875f3e585b703568))

## [0.1.0](https://github.com/fabiocicerchia/gradebook/compare/v0.1.0...v0.1.0) (2026-08-24)

### Features

- grade a repository's tests and code against a weighted rubric ([82222f2](https://github.com/fabiocicerchia/gradebook/commit/82222f2d14721d7c6250fbd621e118f7d1df892e))

## [Unreleased]

### Added

- `gradebook-tests` — scores a repository's test suite 0-100 across classification,
  coverage evidence, TDD discipline, naming, assertion quality, mock placement
  and test smells.
- `gradebook-code` — scores the code itself against twelve weighted principle
  dimensions (DRY, YAGNI, GRASP, SOLID, KISS).

[Unreleased]: https://github.com/fabiocicerchia/gradebook/commits/main
