.PHONY: setup dev test lint format typecheck clean \
        run run-week \
        install-scheduler install-scheduler-weekly \
        uninstall-scheduler uninstall-scheduler-weekly

setup:
	uv sync

dev:
	uv run python -m app.main

run:
	bash run.sh

run-week:
	bash run.sh --week

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
	@echo "Installing macOS launchd daily scheduler (07:30)..."
	cp com.immo-search.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.immo-search.plist
	@echo "Daily scheduler installed."

uninstall-scheduler:
	@echo "Removing macOS launchd daily scheduler..."
	launchctl unload ~/Library/LaunchAgents/com.immo-search.plist
	rm -f ~/Library/LaunchAgents/com.immo-search.plist
	@echo "Daily scheduler removed."

install-scheduler-weekly:
	@echo "Installing macOS launchd weekly scheduler (Saturday 09:00)..."
	cp com.immo-search-weekly.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.immo-search-weekly.plist
	@echo "Weekly scheduler installed. Will run every Saturday at 09:00."

uninstall-scheduler-weekly:
	@echo "Removing macOS launchd weekly scheduler..."
	launchctl unload ~/Library/LaunchAgents/com.immo-search-weekly.plist
	rm -f ~/Library/LaunchAgents/com.immo-search-weekly.plist
	@echo "Weekly scheduler removed."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ .ruff_cache/ .mypy_cache/ .pytest_cache/
	rm -rf output/*.html output/*.csv logs/*.log 2>/dev/null || true
