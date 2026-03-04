.PHONY: setup dev test lint format typecheck clean install-scheduler

setup:
	uv sync

dev:
	uv run python -m app.main

run:
	bash run.sh

test:
	uv run pytest tests/ -v

test-coverage:
	uv run pytest tests/ --cov=app --cov-report=html --cov-report=term

lint:
	uv run ruff check app/ tests/

format:
	uv run black app/ tests/
	uv run ruff check --fix app/ tests/

typecheck:
	uv run mypy app/

install-scheduler:
	@echo "Installing macOS launchd scheduler..."
	cp com.immo-search.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.immo-search.plist
	@echo "Scheduler installed. Will run daily at 07:30."

uninstall-scheduler:
	@echo "Removing macOS launchd scheduler..."
	launchctl unload ~/Library/LaunchAgents/com.immo-search.plist
	rm -f ~/Library/LaunchAgents/com.immo-search.plist
	@echo "Scheduler removed."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ .ruff_cache/ .mypy_cache/ .pytest_cache/
	rm -rf output/*.html output/*.csv logs/*.log 2>/dev/null || true
