# Malaika — common developer commands.
#
# Run `make help` for a full list. Targets are deliberately thin wrappers
# over the canonical tools (ruff, mypy, pytest, flutter, npm) so that the
# tools remain the source of truth.

PYTHON ?= python
PIP ?= pip
RUFF ?= ruff
MYPY ?= mypy
PYTEST ?= pytest
FLUTTER ?= flutter
NPM ?= npm

PY_SRC := malaika tests
FLUTTER_DIR := malaika_flutter
WEB_DIR := web

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help:                ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Python (Tier 1 server, agentic skills, evaluation)
# ---------------------------------------------------------------------------

.PHONY: install
install:             ## Install Python deps in editable mode + dev tools.
	$(PIP) install -e .
	$(PIP) install ruff mypy pytest pytest-cov

.PHONY: lint
lint:                ## Lint Python code (ruff + mypy strict).
	$(RUFF) check $(PY_SRC)
	$(RUFF) format --check $(PY_SRC)
	$(MYPY) malaika --strict

.PHONY: format
format:              ## Auto-format Python code (ruff format + ruff fix).
	$(RUFF) format $(PY_SRC)
	$(RUFF) check --fix $(PY_SRC)

.PHONY: test
test:                ## Run Python tests (excluding GPU-required).
	$(PYTEST) tests -v -m "not gpu_required"

.PHONY: test-all
test-all:            ## Run every Python test, including GPU-required.
	$(PYTEST) tests -v

.PHONY: coverage
coverage:            ## Run tests with coverage; fails under 80%.
	$(PYTEST) tests --cov=malaika --cov-report=term-missing -m "not gpu_required"

.PHONY: golden
golden:              ## Run the 21 golden IMCI scenarios.
	$(PYTHON) -m malaika.evaluation.evaluator

# ---------------------------------------------------------------------------
# Flutter (Tier 0 phone app)
# ---------------------------------------------------------------------------

.PHONY: flutter-install
flutter-install:     ## Fetch Flutter dependencies.
	cd $(FLUTTER_DIR) && $(FLUTTER) pub get

.PHONY: flutter-lint
flutter-lint:        ## Lint Flutter code.
	cd $(FLUTTER_DIR) && $(FLUTTER) analyze

.PHONY: flutter-test
flutter-test:        ## Run Flutter unit tests.
	cd $(FLUTTER_DIR) && $(FLUTTER) test

.PHONY: flutter-build
flutter-build:       ## Build a debug APK.
	cd $(FLUTTER_DIR) && $(FLUTTER) build apk --debug

.PHONY: flutter-build-release
flutter-build-release: ## Build a release APK.
	cd $(FLUTTER_DIR) && $(FLUTTER) build apk --release

# ---------------------------------------------------------------------------
# Web (Tier 2 clinical portal)
# ---------------------------------------------------------------------------

.PHONY: web-install
web-install:         ## Install web dependencies.
	cd $(WEB_DIR) && $(NPM) install

.PHONY: web-lint
web-lint:            ## Lint the web app.
	cd $(WEB_DIR) && $(NPM) run lint

.PHONY: web-build
web-build:           ## Build the web app.
	cd $(WEB_DIR) && $(NPM) run build

.PHONY: web-dev
web-dev:             ## Run the web app in dev mode.
	cd $(WEB_DIR) && $(NPM) run dev

# ---------------------------------------------------------------------------
# Composite targets
# ---------------------------------------------------------------------------

.PHONY: ci
ci: lint test flutter-lint flutter-test web-lint web-build  ## Run everything CI runs.

.PHONY: clean
clean:               ## Remove caches and build artefacts.
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	cd $(FLUTTER_DIR) && $(FLUTTER) clean
	rm -rf $(WEB_DIR)/.next $(WEB_DIR)/node_modules/.cache
