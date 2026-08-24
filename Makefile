# Two independent tools, one entry point. Each folder builds, tests and lints
# on its own; this only saves you from remembering which is which.
TOOLS := gradebook-tests gradebook-code

.PHONY: help install dev lint test test-tests test-code setup check clean

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

setup: ## Install the pre-commit hook
	pre-commit install

check: ## Run all pre-commit checks on the whole tree
	pre-commit run --all-files

clean: ## Remove caches and build artifacts
	rm -rf gradebook-*/.pytest_cache gradebook-*/.ruff_cache gradebook-*/__pycache__ \
	       gradebook-*/tests/__pycache__ gradebook-*/*.egg-info
