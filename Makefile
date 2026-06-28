.DEFAULT_GOAL := help

UV ?= uv
CLIENT_PACKAGE := lewisham-client
SERVER_PACKAGE := lewisham-server
MCP_PACKAGE := lewisham-mcp
CLIENT_DIR := packages/$(CLIENT_PACKAGE)
SERVER_DIR := packages/$(SERVER_PACKAGE)
MCP_DIR := packages/$(MCP_PACKAGE)

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
typecheck: typecheck-client typecheck-server typecheck-mcp ## Run mypy for every package.

.PHONY: typecheck-client
typecheck-client: ## Run mypy for lewisham-client.
	cd $(CLIENT_DIR) && $(UV) run --package $(CLIENT_PACKAGE) mypy src/

.PHONY: typecheck-server
typecheck-server: ## Run mypy for lewisham-server.
	cd $(SERVER_DIR) && $(UV) run --package $(SERVER_PACKAGE) mypy src/

.PHONY: typecheck-mcp
typecheck-mcp: ## Run mypy for lewisham-mcp.
	cd $(MCP_DIR) && $(UV) run --package $(MCP_PACKAGE) mypy src/

.PHONY: test
test: test-client test-server test-mcp ## Run pytest for every package.

.PHONY: test-client
test-client: ## Run lewisham-client tests.
	cd $(CLIENT_DIR) && $(UV) run --package $(CLIENT_PACKAGE) pytest

.PHONY: test-server
test-server: ## Run lewisham-server tests.
	cd $(SERVER_DIR) && $(UV) run --package $(SERVER_PACKAGE) pytest

.PHONY: test-mcp
test-mcp: ## Run lewisham-mcp tests.
	cd $(MCP_DIR) && $(UV) run --package $(MCP_PACKAGE) pytest

.PHONY: server
server: ## Run lewisham-server using its production entrypoint.
	$(UV) run --package $(SERVER_PACKAGE) python -m lewisham_server

.PHONY: server-dev
server-dev: ## Run lewisham-server with uvicorn reload enabled.
	$(UV) run --package $(SERVER_PACKAGE) uvicorn lewisham_server.main:app --reload --no-access-log

.PHONY: mcp
mcp: ## Run the MCP server.
	$(UV) run --package $(MCP_PACKAGE) python -m lewisham_mcp.server

.PHONY: docker-build-server
docker-build-server: ## Build the lewisham-server Docker image.
	docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .

.PHONY: docker-build-mcp
docker-build-mcp: ## Build the lewisham-mcp Docker image.
	docker build -f packages/lewisham-mcp/Dockerfile -t lewisham-mcp .
