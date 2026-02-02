# MAO - Multi-Agent Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Hierarchical AI development system powered by Claude.

## Overview

MAO is a multi-agent orchestration framework that enables complex software development tasks through a hierarchical team of specialized AI agents. Built on Claude API, MAO provides a production-ready system for AI-assisted software development with built-in governance, security review, and skill learning capabilities.

## Architecture

```
User (Approver)
    ↓
🛡️ Auditor (Security & Ethics)
    ↓
📋 Planner ←→ 🔍 Researcher
    ↓
🏗️ Architect
    ↓
Development Pool (dynamic)
├── 🎨 Designer
├── 💻 Coder (Frontend/Backend/API/etc.)
└── ...
    ↓
Quality Assurance
├── 👁️ Reviewer
└── 🧪 Tester
    ↓
Integration
├── 🔧 Integrator
├── 📝 Documentor
└── 🚀 DevOps
```

## Features

- **Hierarchical Agent System**: Specialized agents for governance, planning, development, QA, and integration
- **Dynamic Agent Pool**: Spawn development agents on-demand with specific roles
- **Real-time Monitoring**: Textual TUI dashboard + tmux agent logs
- **Flexible Configuration**: YAML + Markdown role definitions
- **Coding Standards**: Language-specific and project-specific coding standards support
- **State Management**: Redis or SQLite backend
- **Headless Agents**: Agents run in background, logs streamed to tmux
- **Skill Learning**: Automatically extracts reusable patterns and creates skills with security review
- **Built-in Governance**: Security auditing and ethics review before execution

## Installation

MAO uses [uv](https://github.com/astral-sh/uv), a blazing-fast Python package manager, for dependency management.

### Prerequisites

Install uv if not already installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Quick Install

```bash
# One-line installer
curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh
```

The installer will:

- Verify uv is installed
- Create a virtual environment at `~/.mao/venv`
- Install MAO and all dependencies from `pyproject.toml`
- Create executable at `~/.local/bin/mao`
- Optionally add to your PATH

### From Source

```bash
# Clone repository
git clone https://github.com/marusan03/mao.git
cd mao

# Install (auto-installs uv if needed)
./install.sh

# Or for development with uv
uv venv
uv pip install -e .

# Or use the development wrapper
./bin/mao --help
```

## Quick Start

### Agent Execution Modes

MAO supports three execution modes:

**1. Claude Code CLI Mode** (Recommended - No API key required):
- ✅ Run multiple Claude Code instances in parallel
- ✅ Each agent gets its own workspace
- ✅ No API key needed
- ✅ Free to use with Claude Code

Prerequisites:
- Install Claude Code: https://claude.ai/download
- Ensure `claude-code` or `claude` command is available in PATH

**2. API Mode** (Requires API key):
- Uses Anthropic API directly
- Requires ANTHROPIC_API_KEY

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

Get your API key from: https://console.anthropic.com/

**3. Dashboard Only Mode** (No agent execution):
- View project configuration
- Monitor project structure
- Access settings and configuration

MAO automatically detects which mode to use:
1. First tries Claude Code CLI
2. Falls back to API mode if API key is set
3. Dashboard only if neither is available

### Initialize Project

```bash
# Initialize in your project
cd /path/to/your/project
mao init

# Start the orchestrator
mao start

# (Optional) View agent logs in another terminal
tmux attach -t mao
```

### Test Agent Execution

Simple test to verify setup:

```bash
cd mao
python examples/test_agent.py
```

For streaming responses:

```bash
python examples/test_agent_streaming.py
```

### Updating MAO

Keep MAO up to date with the latest features and fixes:

```bash
# Check current version
mao version

# Update to latest version
mao update
```

The `mao version` command shows:
- Current version number
- Git commit hash
- Installation date
- Python and uv versions

The `mao update` command will:
- Show current version
- Check for new commits on GitHub
- Display what's changed (commit log)
- Ask for confirmation before updating
- Pull the latest changes (if installed via git)
- Reinstall dependencies with uv
- Show new version after update
- Preserve your project configurations

## Usage

### Commands

```bash
mao init              # Initialize MAO in current project
mao start             # Start the orchestrator dashboard
mao start --no-tmux   # Start without tmux monitoring
mao config            # Show current configuration
mao roles             # List available agent roles
mao languages         # List supported languages
mao languages python  # Show Python language details
mao version           # Show detailed version information
mao update            # Update MAO to the latest version
mao uninstall         # Uninstall MAO
mao --help            # Show help
mao --version         # Show version (short)
```

### Project Structure

After `mao init`, your project will have:

```sh
your-project/
├── .mao/
│   ├── config.yaml              # Project configuration
│   ├── coding_standards/        # Custom coding standards
│   ├── roles/                   # Custom agent roles (optional)
│   ├── context/                 # Project context documents
│   └── logs/                    # Agent logs (created at runtime)
├── src/
└── ...
```

## Configuration

### Project Configuration (.mao/config.yaml)

```yaml
project_name: my-project
default_language: python

agents:
  default_model: sonnet
  enable_parallel: true
  max_workers: 5

state:
  backend: sqlite  # or redis
```

### Language Configuration

MAO comes with pre-configured language settings for:

- **Python** (PEP 8, Black, Ruff, mypy)
- **TypeScript** (Prettier, ESLint, Airbnb style)
- **JavaScript** (Prettier, ESLint)
- **Go** (gofmt, golangci-lint, Effective Go)
- **Rust** (rustfmt, clippy)

Each language configuration includes:

- Recommended tools (formatter, linter, test framework)
- Default settings (line length, indent size, etc.)
- Coding standards references
- File extensions

View available languages:

```bash
mao languages           # List all supported languages
mao languages python    # Show Python configuration details
```

### Custom Coding Standards

Agents automatically load coding standards based on the project language. You can customize these standards by adding files to `.mao/coding_standards/`:

```markdown
# .mao/coding_standards/python_custom.md

## Project-Specific Rules

### API Endpoints
- Use `/api/v1/` prefix
- Follow RESTful conventions

### Error Handling
- Use custom exception classes
- Log all errors with structlog

### Database
- Use SQLAlchemy ORM
- Migration files in alembic/versions/
```

**How it works:**

1. Default standards are loaded from MAO's built-in templates
2. Project-specific standards from `.mao/coding_standards/<language>_custom.md` are merged
3. Agents receive the combined standards in their context
4. This ensures consistent code style across all generated code

## Skills System

MAO automatically learns from repetitive patterns and creates reusable skills.

### How It Works

1. **Pattern Detection**: Agents detect repeated operations (3+ times)
2. **Skill Extraction**: Skill Extractor agent creates a skill definition
3. **Security Review**: Skill Reviewer evaluates security, quality, and generalization
4. **User Approval**: You review and approve the skill
5. **Reuse**: Use the skill across projects

### Managing Skills

```bash
# List available skills
mao skills list

# Show skill details
mao skills show setup_fastapi

# Run a skill
mao skills run setup_fastapi --project_name=myapi

# Dry run (preview commands)
mao skills run setup_fastapi --project_name=myapi --dry-run

# View pending proposals
mao skills proposals

# Delete a skill
mao skills delete setup_fastapi
```

### Example: Auto-Generated Skill

When agents repeatedly set up FastAPI projects, MAO automatically proposes:

```yaml
name: setup_fastapi
display_name: "FastAPI Project Setup"
description: "Automates FastAPI project initialization"

parameters:
  - name: project_name
    type: string
    required: true
    description: "Project name"

commands:
  - pip install fastapi uvicorn pydantic
  - mkdir -p app/{models,routers,schemas}
  - touch app/__init__.py app/main.py
```

The skill is reviewed for:

- **Security**: No dangerous operations
- **Generalization**: Works across projects
- **Documentation**: Clear and complete
- **Quality**: High reusability score

### Skill Security

All skills undergo automated security review:

- 🔴 **REJECTED**: Hardcoded credentials, arbitrary code execution, destructive commands
- 🟡 **WARNING**: Package installation, file deletion, network access (requires approval)
- ✅ **SAFE**: Read-only operations, new file creation

## Agent Execution Engine

MAO uses Claude API directly for agent execution. Each agent runs as an asynchronous process with streaming support.

### Architecture

```text
Dashboard (Textual UI)
    ↓
AgentExecutor (Anthropic SDK)
    ↓
Multiple Agents (Parallel Execution)
├── Planner
├── Auditor
├── Coder x3
└── Reviewer
    ↓
Logs → tmux panes (monitoring)
```

### Features

- **Async Execution**: Non-blocking parallel agent execution
- **Streaming Support**: Real-time response streaming
- **Token Tracking**: Automatic usage and cost calculation
- **Logging**: Per-agent detailed logs
- **Error Handling**: Robust error recovery

### Example Usage

```python
from mao.orchestrator.agent_executor import AgentExecutor
from mao.orchestrator.agent_logger import AgentLogger

# Initialize
executor = AgentExecutor()
logger = AgentLogger("agent-001", "TestAgent", log_dir)

# Execute agent
result = await executor.execute_agent(
    prompt="Your task here",
    model="claude-sonnet-4-20250514",
    logger=logger,
)

# Or with streaming
async for event in executor.execute_agent_streaming(
    prompt="Your task here",
    model="claude-sonnet-4-20250514",
    logger=logger,
):
    if event["type"] == "content":
        print(event["content"], end="", flush=True)
```

### Supported Models

- **Opus** (`claude-opus-4-20250514`): Most capable, highest cost
- **Sonnet** (`claude-sonnet-4-20250514`): Balanced performance and cost (default)
- **Haiku** (`claude-haiku-4-20250514`): Fast and economical

### Configuration

Set your API key in environment:

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

Or in `.mao/config.yaml`:

```yaml
api:
  anthropic_key: your-api-key-here  # Not recommended for security
```

## Development

```bash
# Clone repository
git clone https://github.com/marusan03/mao.git
cd mao

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with uv
uv venv --python python3.11

# Install in development mode
uv pip install -e .

# Or use the development wrapper (handles uv setup automatically)
./bin/mao --help
```

## Requirements

### Required
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### For Agent Execution (Choose one)
- **Option 1 (Recommended)**: [Claude Code](https://claude.ai/download) - No API key needed
- **Option 2**: Anthropic API key - From https://console.anthropic.com/

### Optional
- tmux - For agent monitoring in separate panes
- Redis - For distributed state management

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/marusan03/mao).

### Areas for Contribution

- Additional agent roles (e.g., Performance Optimizer, Accessibility Specialist)
- Language-specific coding standards
- Skill templates
- UI/UX improvements
- Documentation
- Bug fixes and performance improvements
