#!/bin/bash
set -e

# Multi-Agent Orchestrator Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MAO_VERSION="${MAO_VERSION:-main}"
MAO_REPO="${MAO_REPO:-https://github.com/marusan03/mao}"
MAO_HOME="${HOME}/.mao"
MAO_BIN="${HOME}/.local/bin"
MAO_INSTALL_DIR="${MAO_HOME}/install"

echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║  Multi-Agent Orchestrator (MAO) Installer     ║
║  Hierarchical AI Development System           ║
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

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        *)          echo "unknown" ;;
    esac
}

OS=$(detect_os)
if [ "$OS" = "unknown" ]; then
    error "Unsupported operating system"
fi

success "Detected OS: $OS"

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

# Check optional dependencies
info "Checking optional dependencies..."

if command_exists tmux; then
    success "tmux found - agent monitoring enabled"
    HAS_TMUX=1
else
    warn "tmux not found - agent monitoring will be disabled"
    warn "Install tmux for better agent visualization:"
    if [ "$OS" = "macos" ]; then
        echo "    brew install tmux"
    else
        echo "    sudo apt-get install tmux  # or yum install tmux"
    fi
    HAS_TMUX=0
fi

if command_exists redis-server; then
    success "Redis found - distributed state management available"
    HAS_REDIS=1
else
    warn "Redis not found - will use SQLite (single-node only)"
    if [ "$OS" = "macos" ]; then
        echo "    brew install redis"
    else
        echo "    sudo apt-get install redis-server"
    fi
    HAS_REDIS=0
fi

echo ""

# Create directories
info "Creating directories..."
mkdir -p "${MAO_HOME}"
mkdir -p "${MAO_BIN}"
mkdir -p "${MAO_INSTALL_DIR}"
success "Directories created"

# Download or clone repository
info "Downloading MAO..."

# For local installation (during development)
if [ -f "$(dirname "$0")/pyproject.toml" ]; then
    info "Installing from local directory..."
    INSTALL_SOURCE="$(cd "$(dirname "$0")" && pwd)"
else
    # Remote installation
    if [ -d "${MAO_INSTALL_DIR}/.git" ]; then
        info "Updating existing installation..."
        cd "${MAO_INSTALL_DIR}"
        git pull origin "${MAO_VERSION}" >/dev/null 2>&1 || warn "Failed to update"
    else
        if command_exists git; then
            git clone --depth 1 --branch "${MAO_VERSION}" "${MAO_REPO}" "${MAO_INSTALL_DIR}" >/dev/null 2>&1
        else
            # Fallback to curl/wget for tarball
            TARBALL_URL="${MAO_REPO}/archive/refs/heads/${MAO_VERSION}.tar.gz"
            if command_exists curl; then
                curl -fsSL "${TARBALL_URL}" | tar -xz -C "${MAO_INSTALL_DIR}" --strip-components=1
            elif command_exists wget; then
                wget -qO- "${TARBALL_URL}" | tar -xz -C "${MAO_INSTALL_DIR}" --strip-components=1
            else
                error "git, curl, or wget is required"
            fi
        fi
    fi
    INSTALL_SOURCE="${MAO_INSTALL_DIR}"
fi

success "Source location: ${INSTALL_SOURCE}"

# Create virtual environment with uv
info "Creating virtual environment with uv..."
uv venv "${MAO_HOME}/venv" --python python3.11

# Install package
info "Installing MAO and dependencies with uv..."
uv pip install --python "${MAO_HOME}/venv/bin/python" -e "${INSTALL_SOURCE}"
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
        if [ "$OS" = "macos" ]; then
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
if [ $HAS_TMUX -eq 1 ]; then
    echo "  • tmux: enabled ✓"
else
    echo "  • tmux: not available"
fi
if [ $HAS_REDIS -eq 1 ]; then
    echo "  • Redis: available ✓"
else
    echo "  • Redis: not available (SQLite mode)"
fi

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
echo "  5. (Optional) In another terminal, view agent logs:"
echo -e "     ${GREEN}tmux attach -t mao${NC}"
echo ""
echo "For help:"
echo -e "  ${GREEN}mao --help${NC}"
echo ""
echo "To uninstall:"
echo -e "  ${GREEN}mao uninstall${NC}"
echo ""
