#!/usr/bin/env bash
# Development environment setup script
# Uses mise for tool version management

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Setting up MAO development environment${NC}\n"

# Check if mise is installed
if ! command -v mise &> /dev/null; then
    echo -e "${RED}❌ mise is not installed${NC}"
    echo -e "${YELLOW}Install mise:${NC}"
    echo "  curl https://mise.run | sh"
    echo "  or: brew install mise"
    echo ""
    echo "Then add to your shell config (~/.bashrc or ~/.zshrc):"
    echo '  eval "$(mise activate bash)"  # or zsh'
    exit 1
fi

echo -e "${GREEN}✓ mise found${NC}"

# Install tools defined in .mise.toml
echo -e "\n${YELLOW}📦 Installing tools...${NC}"
mise install

# Activate mise environment
echo -e "\n${YELLOW}🔧 Activating mise environment...${NC}"
eval "$(mise activate bash)"

# Install Python dependencies
echo -e "\n${YELLOW}📚 Installing Python dependencies...${NC}"
mise run install

# Install pre-commit hooks
echo -e "\n${YELLOW}🪝 Installing pre-commit hooks...${NC}"
mise run pre-commit-install

# Run initial quality check
echo -e "\n${YELLOW}✨ Running initial quality check...${NC}"
mise run quality || {
    echo -e "\n${YELLOW}⚠️  Some quality issues found. Run 'mise run quality-fix' to auto-fix${NC}"
}

echo -e "\n${GREEN}✅ Development environment setup complete!${NC}"
echo -e "\n${YELLOW}Quick commands:${NC}"
echo "  mise run quality       - Run code quality checks"
echo "  mise run quality-fix   - Run checks with auto-fix"
echo "  mise run test          - Run tests"
echo "  mise run lint          - Lint only"
echo "  mise run format        - Format check only"
echo "  mise run typecheck     - Type check only"
echo ""
echo "Or use Makefile:"
echo "  make quality"
echo "  make test"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
