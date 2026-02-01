#!/usr/bin/env bash
# Code quality checker - runs ruff and pyright
# Usage: ./scripts/check_code_quality.sh [--fix]
# Note: Use mise for automatic tool version management

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
fi

echo -e "${GREEN}🔍 Running code quality checks...${NC}\n"

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo -e "${RED}❌ ruff not found. Install with: pip install ruff${NC}"
    exit 1
fi

# Check if pyright is installed
if ! command -v pyright &> /dev/null; then
    echo -e "${YELLOW}⚠️  pyright not found. Install with: pip install pyright${NC}"
    PYRIGHT_AVAILABLE=false
else
    PYRIGHT_AVAILABLE=true
fi

# Run ruff linter
echo -e "${YELLOW}📋 Running ruff linter...${NC}"
if [ "$FIX_MODE" = true ]; then
    ruff check --fix mao/ tests/
    echo -e "${GREEN}✅ Ruff linter (with fixes)${NC}\n"
else
    ruff check mao/ tests/
    echo -e "${GREEN}✅ Ruff linter${NC}\n"
fi

# Run ruff formatter
echo -e "${YELLOW}🎨 Running ruff formatter...${NC}"
if [ "$FIX_MODE" = true ]; then
    ruff format mao/ tests/
    echo -e "${GREEN}✅ Ruff formatter (applied)${NC}\n"
else
    ruff format --check mao/ tests/
    echo -e "${GREEN}✅ Ruff formatter${NC}\n"
fi

# Run pyright type checker
if [ "$PYRIGHT_AVAILABLE" = true ]; then
    echo -e "${YELLOW}🔎 Running pyright type checker...${NC}"
    pyright mao/
    echo -e "${GREEN}✅ Pyright type checker${NC}\n"
fi

# Run custom mutable defaults checker
echo -e "${YELLOW}🔒 Checking for mutable default patterns...${NC}"
if python3 scripts/check_mutable_defaults.py mao/**/*.py; then
    echo -e "${GREEN}✅ No mutable default patterns${NC}\n"
else
    echo -e "${RED}❌ Mutable default patterns found${NC}"
    echo -e "${YELLOW}See docs/CODING_STANDARDS.md for correct patterns${NC}\n"
    exit 1
fi

echo -e "${GREEN}🎉 All checks passed!${NC}"
