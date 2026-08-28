# Two independent tools, one entry point. Each folder builds, tests and lints
# on its own; this only saves you from remembering which is which.
TOOLS := gradebook-tests gradebook-code
EXT_DIR := extensions/vscode
# Read rather than hard-coded: vsce names the VSIX after the version in the
# manifest, so a release bump must not turn ext-install into "file not found".
EXT_VERSION := $(shell node -p "require('./$(EXT_DIR)/package.json').version" 2>/dev/null)
VSIX := $(EXT_DIR)/gradebook-$(EXT_VERSION).vsix

.PHONY: help install dev lint test test-tests test-code test-nvim setup check clean \
        ext-build ext-package ext-install ext-publish

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-11s %s\n", $$1, $$2}'

install: ## pip install both tools
	@for tool in $(TOOLS); do $(MAKE) -C . install-$$tool; done

install-%:
	pip install ./$*

dev: ## Editable installs of both, plus pytest and ruff
	pip install -e ./gradebook-tests -e ./gradebook-code pytest ruff

lint: ## ruff over both tools
	cd gradebook-tests && ruff check .
	cd gradebook-code && ruff check .

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

setup: ## Install the pre-commit hook
	pre-commit install

check: ## Run all pre-commit checks on the whole tree
	pre-commit run --all-files

clean: ## Remove caches and build artifacts
	rm -rf gradebook-*/.pytest_cache gradebook-*/.ruff_cache gradebook-*/__pycache__ \
	       gradebook-*/tests/__pycache__ gradebook-*/*.egg-info \
	       $(EXT_DIR)/node_modules $(EXT_DIR)/out $(EXT_DIR)/out-tsc \
	       $(EXT_DIR)/*.vsix $(EXT_DIR)/LICENSE $(EXT_DIR)/CHANGELOG.md \
	       extensions/nvim/.deps
