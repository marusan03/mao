.PHONY: help lint format typecheck quality quality-fix test install-dev pre-commit-install

help:
	@echo "MAO Development Commands"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Check code formatting with ruff"
	@echo "  make format-fix    - Fix code formatting with ruff"
	@echo "  make typecheck     - Run pyright type checker"
	@echo "  make quality       - Run all quality checks (lint + format + typecheck)"
	@echo "  make quality-fix   - Run all checks with auto-fix"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests with pytest"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo ""
	@echo "Setup:"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make pre-commit-install - Install pre-commit hooks"
	@echo ""

# Code quality targets
lint:
	@echo "🔍 Running ruff linter..."
	ruff check mao/ tests/

lint-fix:
	@echo "🔍 Running ruff linter with auto-fix..."
	ruff check --fix mao/ tests/

format:
	@echo "🎨 Checking code formatting..."
	ruff format --check mao/ tests/

format-fix:
	@echo "🎨 Fixing code formatting..."
	ruff format mao/ tests/

typecheck:
	@echo "🔎 Running type checker..."
	pyright mao/

quality:
	@echo "🚀 Running all code quality checks..."
	@./scripts/check_code_quality.sh

quality-fix:
	@echo "🚀 Running all code quality checks with auto-fix..."
	@./scripts/check_code_quality.sh --fix

# Testing targets
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

test-e2e:
	@echo "🧪 Running e2e tests..."
	pytest tests/e2e/ -v

# Setup targets
install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -e ".[dev]"

pre-commit-install:
	@echo "🪝 Installing pre-commit hooks..."
	pre-commit install
	@echo "✅ Pre-commit hooks installed. They will run automatically on git commit."

# Convenience target - setup everything
setup: install-dev pre-commit-install
	@echo "✅ Development environment setup complete!"
