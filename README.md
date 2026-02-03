# MAO - Multi-Agent Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Hierarchical AI development system powered by Claude Code.

## Overview

MAO is a multi-agent orchestration framework that runs multiple Claude Code CLI instances in parallel within tmux. A CTO (Chief Technology Officer) agent coordinates the work, delegating tasks to specialized agents through YAML-based communication.

## Architecture

```
User
  ↓ (mao start "task")
CTO (tmux pane 0: Interactive Claude Code)
  ├→ Agent-1 (tmux pane 1: Interactive Claude Code)
  ├→ Agent-2 (tmux pane 2: Interactive Claude Code)
  └→ ... (dynamically spawned as needed)

[Optional] Dashboard: Progress & log monitoring
```

## Key Features

- **tmux-centric**: All agents run as interactive Claude Code instances in tmux panes
- **CTO-led orchestration**: CTO decomposes tasks and coordinates agents
- **YAML-based communication**: Agents communicate via `.mao/queue/tasks/` and `.mao/queue/reports/`
- **No `--print` mode**: All Claude Code instances run interactively
- **Optional dashboard**: TUI for monitoring progress (not required)

## Requirements

- **tmux** (required): `brew install tmux` or `apt install tmux`
- **Claude Code CLI** (required): https://claude.ai/download
- **Python 3.11+**
- **uv** (optional): https://github.com/astral-sh/uv

## Installation

```bash
# Clone repository
git clone https://github.com/marusan03/mao.git
cd mao

# Install with pip or uv
pip install -e .
# or
uv pip install -e .
```

## Quick Start

### 1. Initialize your project

```bash
cd your-project
mao init
```

### 2. Start MAO with a task

```bash
mao start "Implement authentication system"
```

This will:
1. Create a tmux session with CTO + agent panes
2. Start CTO in pane 0 with your task
3. CTO will decompose the task and delegate to agents

### 3. Interact with agents

```bash
# Attach to tmux session
tmux attach -t mao

# Navigate between panes
Ctrl+B → arrow keys

# Zoom into a pane
Ctrl+B → z

# Detach from session
Ctrl+B → d
```

### 4. (Optional) Launch dashboard for monitoring

```bash
# In a separate terminal
mao dashboard
```

## Usage

### Commands

```bash
mao start "task"              # Start MAO with a task
mao start --dashboard "task"  # Start with dashboard
mao dashboard                 # Launch dashboard for existing session
mao init                      # Initialize MAO in project
mao sandbox start "task"      # Start MAO in Docker Sandbox
mao sandbox attach            # Attach to existing sandbox
mao --help                    # Show help
```

### Options

```bash
mao start [OPTIONS] [PROMPT]

Options:
  -p, --project-dir PATH       Project directory (default: current)
  -t, --task TEXT             Task prompt (alternative to PROMPT)
  --model [sonnet|opus|haiku]  Model for CTO (default: sonnet)
  -n, --num-agents INTEGER     Number of agent panes (default: 4)
  --dashboard                  Also launch dashboard
  -s, --session TEXT          Continue from session ID
  --new-session               Always create new session
```

## Docker Sandbox Mode (Optional)

For enhanced security, run MAO inside a Docker Sandbox (MicroVM):

```bash
# Build MAO sandbox template (first time only)
mao sandbox build

# Start MAO in isolated sandbox
mao sandbox start "Implement authentication"

# Attach to existing sandbox
mao sandbox attach

# List all sandboxes
mao sandbox ls
```

Docker Sandboxes protect your host system while allowing MAO to operate normally. Requires Docker Desktop with AI Sandboxes enabled.

See [docs/SANDBOX.md](docs/SANDBOX.md) for details.

## How It Works

### 1. Task Distribution

CTO creates YAML task files for agents:

```yaml
# .mao/queue/tasks/agent-1.yaml
task_id: task-001
role: agent-1
prompt: |
  Implement the login API endpoint.
  - POST /api/login
  - JWT authentication
model: sonnet
status: ASSIGNED
```

### 2. Agent Execution

Each agent runs interactively in its tmux pane, picking up tasks from the queue.

### 3. Result Reporting

Agents report results via YAML:

```yaml
# .mao/queue/reports/agent-1.yaml
task_id: task-001
role: agent-1
status: COMPLETED
result: |
  Implemented login API.
  - Created src/api/auth.py
  - Added tests
```

### 4. CTO Review

CTO reviews results and either approves, requests changes, or escalates to user.

## tmux Session Layout

```
┌─ CTO ─────────┬─ Agent-1 ─────┬─ Agent-2 ─────┐
│               │               │               │
│ Claude Code   │ Claude Code   │ Claude Code   │
│ (interactive) │ (interactive) │ (interactive) │
│               │               │               │
├───────────────┼───────────────┼───────────────┤
│ Agent-3       │ Agent-4       │ Agent-5       │
│               │               │               │
│ Claude Code   │ Claude Code   │ Claude Code   │
│ (waiting)     │ (waiting)     │ (waiting)     │
│               │               │               │
└───────────────┴───────────────┴───────────────┘
```

## Project Structure

```
your-project/
├── .mao/
│   ├── config.yaml           # Project configuration
│   ├── queue/
│   │   ├── tasks/           # CTO → Agent tasks
│   │   └── reports/         # Agent → CTO reports
│   ├── logs/                # Agent logs
│   └── sessions/            # Session data
└── ...
```

## Configuration

### .mao/config.yaml

```yaml
project_name: my-project
default_language: python

defaults:
  tmux:
    grid:
      width: 240
      height: 60
      num_agents: 4

security:
  allow_unsafe_operations: false
```

## Troubleshooting

### tmux not found

```bash
# macOS
brew install tmux

# Ubuntu
sudo apt install tmux
```

### Claude Code not found

Install Claude Code from: https://claude.ai/download

Make sure `claude` command is in your PATH:

```bash
which claude
```

### Session already exists

```bash
# Kill existing session
tmux kill-session -t mao

# Then restart
mao start "your task"
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/marusan03/mao).
