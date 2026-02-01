#!/bin/bash
# MAO Test Runner Script

set -e

echo "======================================"
echo "MAO Test Suite Runner"
echo "======================================"
echo ""

# Check if pytest is installed
if ! ./venv/bin/pytest --version > /dev/null 2>&1; then
    echo "Installing pytest..."
    ./venv/bin/pip install pytest pytest-asyncio
fi

# Run tests based on argument
case "${1:-all}" in
    unit)
        echo "Running unit tests..."
        ./venv/bin/pytest tests/unit/ -v
        ;;
    integration)
        echo "Running integration tests..."
        ./venv/bin/pytest tests/integration/ -v
        ;;
    e2e)
        echo "Running E2E tests..."
        ./venv/bin/pytest tests/e2e/ -v
        ;;
    coverage)
        echo "Running tests with coverage..."
        ./venv/bin/pip install pytest-cov > /dev/null 2>&1 || true
        ./venv/bin/pytest tests/ --cov=mao --cov-report=html --cov-report=term
        echo ""
        echo "Coverage report generated: htmlcov/index.html"
        ;;
    all|*)
        echo "Running all tests..."
        ./venv/bin/pytest tests/ -v
        ;;
esac

echo ""
echo "======================================"
echo "Test run completed!"
echo "======================================"
