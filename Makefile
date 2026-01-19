.PHONY: test test-cov test-cov-html test-cov-xml type type-strict lint format clean help install install-dev

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	pip install -e .

install-audio: ## Install audio only
	pip install -e ".[audio]"

install-image: ## Install image only
	pip install -e ".[image]"

install-video: ## Install image only
	pip install -e ".[video]"

install-dev: ## Install package with dev dependencies
	pip install -e ".[dev]"

test: ## Run unit tests only (no coverage)
	pytest tests/ -v

test-cov: ## Run tests with terminal coverage report
	pytest tests/ --cov=ghostbit --cov-report=term-missing

test-cov-html: ## Run tests with html coverage report
	pytest tests/ --cov=ghostbit --cov-report=html -v

test-cov-xml: ## Run tests with xml coverage report
	pytest tests/ --cov=ghostbit --cov-report=xml -v

type: ## Run type checking only
	mypy src/ghostbit/

type-strict: ## Run type checking with strict mode
	mypy src/ghostbit/ --strict

lint: ## Run linting
	ruff check .

format: ## Format code
	black .

clean: ## Clean up generated files
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf dist/
	rm -rf sdist/
	rm -rf build/
	rm -rf logs/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf src/logs
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

clean-build: ## Clean build artifacts only
	rm -rf dist/
	rm -rf sdist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

clean-test: ## Clean test artifacts only
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

build: clean ## Build package
	python -m build --wheel

all: clean install-dev test