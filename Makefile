.PHONY: help install db-start db-stop init scrape serve test clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies with uv"
	@echo "  make db-start   - Start PostgreSQL with Docker"
	@echo "  make db-stop    - Stop PostgreSQL"
	@echo "  make init       - Initialize database"
	@echo "  make scrape     - Scrape and process 5 meetings"
	@echo "  make serve      - Start API server"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up generated files"

install:
	cd backend && uv sync

db-start:
	docker-compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3

db-stop:
	docker-compose down

init: db-start
	cd backend && python main.py init

scrape:
	cd backend && python main.py run --limit 5

serve:
	cd backend && python main.py serve

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf data/

# Quick setup for first time
setup: install db-start init scrape
	@echo "✓ Setup complete! Run 'make serve' to start the API"

