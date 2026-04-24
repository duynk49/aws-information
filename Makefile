.PHONY: help format lint type-check test install install-dev clean pre-commit-install

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev: install  ## Install development dependencies
	pip install ruff mypy pre-commit

format:  ## Format code with ruff
	ruff format .

lint:  ## Lint code with ruff
	ruff check .

lint-fix:  ## Lint and fix code with ruff
	ruff check --fix .

type-check:  ## Type check with mypy
	mypy .

check: format lint-fix type-check  ## Run all code quality checks

clean:  ## Clean up cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete

pre-commit-install:  ## Install pre-commit hooks
	pre-commit install

pre-commit-run:  ## Run pre-commit on all files
	pre-commit run --all-files

# AWS specific tasks
aws-infra:  ## Run AWS infrastructure collection (requires account parameter)
	@echo "Usage: make aws-infra ACCOUNT=account-name"
	@if [ -z "$(ACCOUNT)" ]; then echo "Please specify ACCOUNT=account-name"; exit 1; fi
	./aws.py infra --account $(ACCOUNT)

aws-billing:  ## Run AWS billing collection (requires account and month parameters)
	@echo "Usage: make aws-billing ACCOUNT=account-name MONTH=2026-04"
	@if [ -z "$(ACCOUNT)" ]; then echo "Please specify ACCOUNT=account-name"; exit 1; fi
	@if [ -z "$(MONTH)" ]; then echo "Please specify MONTH=YYYY-MM"; exit 1; fi
	./aws.py billing --account $(ACCOUNT) --month $(MONTH)

aws-config:  ## Run AWS configuration management
	./aws.py config