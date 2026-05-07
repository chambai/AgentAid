.PHONY: install dev test lint typecheck clean server web agent digest

install:
	uv sync
	pnpm install

dev:
	@echo "Run \`make server\` and \`make web\` in separate terminals."

server:
	uv run uvicorn agentaid_server.main:app --reload --port $${AGENTAID_API_PORT:-8000}

web:
	pnpm --filter agentaid-web dev

agent:
	uv run python -m arxiv_agent

digest:
	AGENTAID_API_PORT=$${AGENTAID_API_PORT:-8000} pnpm --filter arxiv-digest-web dev

test:
	uv run pytest
	pnpm -r test

lint:
	uv run ruff check .
	pnpm -r lint

typecheck:
	uv run mypy packages/agentaid-py/src packages/agentaid-server/src packages/reference-agent/src
	pnpm -r typecheck

clean:
	rm -rf .venv node_modules packages/*/node_modules packages/*/dist packages/*/.venv
