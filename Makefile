.DEFAULT_GOAL := help

UV ?= uv
CLIENT_PACKAGE := lewisham-council-client
SERVER_PACKAGE := lewisham-server
CLIENT_DIR := packages/$(CLIENT_PACKAGE)
SERVER_DIR := packages/$(SERVER_PACKAGE)

.PHONY: help
help: ## Show available targets.
	@awk 'BEGIN {FS = ":.*##"; print "Usage: make <target>\n\nTargets:"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-22s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install all workspace packages and development dependencies.
	$(UV) sync --all-packages --all-groups

.PHONY: lock
lock: ## Refresh the workspace lockfile.
	$(UV) lock

.PHONY: check
check: lint format-check typecheck test ## Run the full local verification suite.

.PHONY: lint
lint: ## Run Ruff linting for the workspace.
	$(UV) run ruff check .

.PHONY: format
format: ## Format the workspace with Ruff (includes import sorting).
	$(UV) run ruff check --fix --select I .
	$(UV) run ruff format .

.PHONY: format-check
format-check: ## Check workspace formatting with Ruff.
	$(UV) run ruff format --check .

.PHONY: typecheck
typecheck: typecheck-client typecheck-server ## Run mypy for every package.

.PHONY: typecheck-client
typecheck-client: ## Run mypy for lewisham-council-client.
	cd $(CLIENT_DIR) && $(UV) run --package $(CLIENT_PACKAGE) mypy src/

.PHONY: typecheck-server
typecheck-server: ## Run mypy for lewisham-server.
	cd $(SERVER_DIR) && $(UV) run --package $(SERVER_PACKAGE) mypy src/

.PHONY: test
test: test-client test-server ## Run pytest for every package.

.PHONY: test-client
test-client: ## Run lewisham-council-client tests.
	cd $(CLIENT_DIR) && $(UV) run --package $(CLIENT_PACKAGE) pytest

.PHONY: test-server
test-server: ## Run lewisham-server tests.
	cd $(SERVER_DIR) && $(UV) run --package $(SERVER_PACKAGE) pytest

.PHONY: server
server: ## Run lewisham-server using its production entrypoint.
	$(UV) run --package $(SERVER_PACKAGE) python -m lewisham_server

.PHONY: server-dev
server-dev: ## Run lewisham-server with uvicorn reload enabled.
	$(UV) run --package $(SERVER_PACKAGE) uvicorn lewisham_server.main:app --reload --no-access-log

.PHONY: docker-build-server
docker-build-server: ## Build the lewisham-server Docker image.
	docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
