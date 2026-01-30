#!/bin/bash
set -e

# MAO Local Installer (for private repositories)
# Usage: ./install-local.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MAO_HOME="${HOME}/.mao"
MAO_BIN="${HOME}/.local/bin"

echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║  MAO Local Installer                          ║
║  Installing from local directory              ║
╚═══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
info "Checking Python version..."
if ! command_exists python3; then
    error "Python 3 is not installed. Please install Python 3.11 or higher."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

version_ge() {
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

if ! version_ge "$PYTHON_VERSION" "$REQUIRED_VERSION"; then
    error "Python 3.11+ required (found $PYTHON_VERSION)"
fi

success "Python $PYTHON_VERSION found"

# Check uv
info "Checking uv..."
if ! command_exists uv; then
    echo ""
    error "uv is not installed. Please install uv first:

    curl -LsSf https://astral.sh/uv/install.sh | sh

Or visit: https://github.com/astral-sh/uv"
fi

UV_VERSION=$(uv --version | cut -d' ' -f2)
success "uv $UV_VERSION found"

# Create directories
info "Creating directories..."
mkdir -p "${MAO_HOME}"
mkdir -p "${MAO_BIN}"
success "Directories created"

# Create virtual environment with uv
info "Creating virtual environment with uv..."
uv venv "${MAO_HOME}/venv" --python python3.11

# Install package from local directory
info "Installing MAO from local directory..."
uv pip install --python "${MAO_HOME}/venv/bin/python" -e "${SCRIPT_DIR}"
success "MAO installed"

# Create wrapper script
info "Creating executable..."
cat > "${MAO_BIN}/mao" << 'WRAPPER_EOF'
#!/bin/bash
# MAO executable wrapper

MAO_HOME="${HOME}/.mao"
MAO_VENV="${MAO_HOME}/venv"

if [ ! -d "${MAO_VENV}" ]; then
    echo "Error: MAO installation not found"
    echo "Please run the installer again"
    exit 1
fi

# Run with uv venv python
exec "${MAO_VENV}/bin/python" -m mao.cli "$@"
WRAPPER_EOF

chmod +x "${MAO_BIN}/mao"
success "Executable created at ${MAO_BIN}/mao"

# Add to PATH if needed
echo ""
if [[ ":$PATH:" != *":${MAO_BIN}:"* ]]; then
    warn "${MAO_BIN} is not in your PATH"
    echo ""

    # Detect shell
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="${HOME}/.zshrc"
        SHELL_NAME="zsh"
    elif [ -n "$BASH_VERSION" ]; then
        if [ "$(uname)" = "Darwin" ]; then
            SHELL_RC="${HOME}/.zprofile"
            SHELL_NAME="zsh"
        else
            SHELL_RC="${HOME}/.bashrc"
            SHELL_NAME="bash"
        fi
    else
        SHELL_RC="${HOME}/.profile"
        SHELL_NAME="shell"
    fi

    echo "Add the following to your ${SHELL_RC}:"
    echo ""
    echo -e "${GREEN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""

    # Ask to add automatically
    read -p "Add to ${SHELL_RC} automatically? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! grep -q ".local/bin" "${SHELL_RC}" 2>/dev/null; then
            echo "" >> "${SHELL_RC}"
            echo "# Added by MAO installer" >> "${SHELL_RC}"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${SHELL_RC}"
            success "Added to ${SHELL_RC}"

            # Apply immediately if possible
            export PATH="$HOME/.local/bin:$PATH"
        else
            info "PATH already configured in ${SHELL_RC}"
        fi
    fi
else
    success "PATH is already configured"
fi

# Installation summary
echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║         Installation Complete! 🎉             ║
╚═══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo "Installation Summary:"
echo "  • Location: ${MAO_HOME}"
echo "  • Executable: ${MAO_BIN}/mao"
echo "  • Python: $PYTHON_VERSION"
echo "  • uv: $UV_VERSION"
echo "  • Source: ${SCRIPT_DIR}"

echo ""
echo "Quick Start:"
echo ""
echo "  1. Start a new terminal or run:"
echo -e "     ${GREEN}source ${SHELL_RC}${NC}"
echo ""
echo "  2. Navigate to your project:"
echo -e "     ${GREEN}cd /path/to/your/project${NC}"
echo ""
echo "  3. Initialize MAO:"
echo -e "     ${GREEN}mao init${NC}"
echo ""
echo "  4. Start the orchestrator:"
echo -e "     ${GREEN}mao start${NC}"
echo ""
echo "For help:"
echo -e "  ${GREEN}mao --help${NC}"
echo ""
