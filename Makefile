.PHONY: install dev run test lint format clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	streamlit run src/app.py

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf dist/ build/ *.egg-info
