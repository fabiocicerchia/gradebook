# Two independent tools, one entry point. Each folder builds, tests and lints
# on its own; this only saves you from remembering which is which.
TOOLS := gradebook-tests gradebook-code
EXT_DIR := extensions/vscode
# Read rather than hard-coded: vsce names the VSIX after the version in the
# manifest, so a release bump must not turn ext-install into "file not found".
EXT_VERSION := $(shell node -p "require('./$(EXT_DIR)/package.json').version" 2>/dev/null)
VSIX := $(EXT_DIR)/gradebook-$(EXT_VERSION).vsix

# Which tool `make run` runs, and what it passes.
TOOL ?= gradebook-code
ARGS ?= --help

# Every verb this repository exposes lives here; `make` on its own prints them.
# FC-GEN-057: the same eight verbs in every repo, each either wired or a
# declared no-op that says why. None of them exit 0 quietly.

.DEFAULT_GOAL := help

.PHONY: help setup install build run test test-tests test-code test-nvim \
        lint format analyze clean \
        ext-build ext-package ext-install ext-publish

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-11s %s\n", $$1, $$2}'

install: ## pip install both tools
	@for tool in $(TOOLS); do $(MAKE) -C . install-$$tool; done

install-%:
	pip install ./$*

# Editable, so a change to either tool is live without reinstalling — plus the
# test and lint tooling and the hook. This absorbed the old `dev` target.
setup: ## Editable installs of both tools, dev tooling, and the pre-commit hook
	pip install -e ./gradebook-tests -e ./gradebook-code pytest ruff
	pre-commit install

# TOOL is the directory name, the module is the same with underscores.
run: ## Run one tool from the checkout (TOOL=gradebook-code, ARGS=--help)
	cd $(TOOL) && python3 -m $(subst -,_,$(TOOL)) $(ARGS)

lint: ## Run the whole gate — every hook, every file
	pre-commit run --all-files

format: ## Format everything the gate checks — both tools, and the extension
	cd gradebook-tests && ruff format .
	cd gradebook-code && ruff format .
	npx --yes @biomejs/biome@2.5.7 format --write .

analyze: ## Scan the tree the way CI does — vulnerabilities, misconfig, secrets
	@command -v trivy >/dev/null 2>&1 || { \
		echo "analyze needs trivy: https://trivy.dev/latest/getting-started/installation/" >&2; \
		exit 69; }
	trivy fs --scanners vuln,misconfig,secret --severity CRITICAL,HIGH .

# --- Declared no-op (FC-GEN-058) ---

build: ## Not applicable — nothing is compiled here
	@echo "Nothing to build: two pure-Python packages, installed from source by"
	@echo "'make install'. The VS Code extension is 'make ext-build'."
	@echo "See README > Not applicable."

test: test-tests test-code ## Run both suites

test-tests: ## Run the gradebook-tests suite
	cd gradebook-tests && pytest -q

test-code: ## Run the gradebook-code suite
	cd gradebook-code && pytest -q

test-nvim: ## Run the Neovim plugin specs (needs nvim)
	$(MAKE) -C extensions/nvim test

# The extension drives the installed tools rather than bundling them, so
# `make install` (or a pipx install) is the other half of this. Node is
# build-time for this folder only — both Python packages, and the scan server
# the extension ships, stay at `dependencies = []`.
#
# The same four extension verbs, with the same meanings, in gandalf, greenlint
# and depwatch: build compiles, package writes the .vsix, install side-loads
# it, publish pushes it to both marketplaces.
ext-build: ## Compile the VS Code extension
	cd $(EXT_DIR) && { [ -d node_modules ] || npm install; } && npm run typecheck && npm run build

ext-package: ext-build ## Build the VS Code extension into a .vsix
	cd $(EXT_DIR) && rm -f ./*.vsix && npm run package

ext-install: ext-package ## Build the VS Code extension and install it
	@command -v code >/dev/null 2>&1 || { \
	  echo "make: the 'code' CLI is not on PATH."; \
	  echo "In VS Code run: Shell Command: Install 'code' command in PATH,"; \
	  echo "or install $(VSIX) from the Extensions view (... > Install from VSIX)."; \
	  exit 1; }
	code --install-extension $(VSIX) --force

# Normally CI's business: publishing happens in publish-extension.yml, called by
# release.yml when release-please cuts a release. This is the manual escape
# hatch, and it needs VSCE_PAT and OVSX_PAT in the environment.
ext-publish: ext-package ## Publish the .vsix to both marketplaces
	cd $(EXT_DIR) && npm run publish -- --packagePath "$(notdir $(VSIX))"
	cd $(EXT_DIR) && npx --yes ovsx@1.1.1 publish "$(notdir $(VSIX))" -p "$$OVSX_PAT"

clean: ## Remove caches and build artifacts
	rm -rf gradebook-*/.pytest_cache gradebook-*/.ruff_cache gradebook-*/__pycache__ \
	       gradebook-*/tests/__pycache__ gradebook-*/*.egg-info \
	       $(EXT_DIR)/node_modules $(EXT_DIR)/out $(EXT_DIR)/out-tsc \
	       $(EXT_DIR)/*.vsix $(EXT_DIR)/LICENSE $(EXT_DIR)/CHANGELOG.md \
	       extensions/nvim/.deps
