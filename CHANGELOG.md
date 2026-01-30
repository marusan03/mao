# Changelog

All notable changes to MAO (Multi-Agent Orchestrator) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Claude Code CLI Integration** - Execute agents using Claude Code CLI
  - No API key required when using Claude Code
  - Parallel execution of multiple Claude Code instances
  - Each agent gets dedicated workspace in `.mao/agents/`
  - Automatic detection and fallback to API mode
  - Documentation: `docs/CLAUDE_CODE_INTEGRATION.md`
- Version management system
  - `mao version` command for detailed version information
  - `mao --version` for quick version check
  - Version display in update command
- Update functionality
  - `mao update` command to update from GitHub
  - Shows commit log before updating
  - Automatic dependency reinstall with uv
- Language configuration system
  - Pre-configured settings for Python, TypeScript, JavaScript, Go, Rust
  - `mao languages` command to list and view language configs
  - Coding standards templates
  - ConfigLoader for loading language settings
- Enhanced dashboard UI
  - Real-time task progress tracking
  - Agent activity feed
  - Metrics widget with Claude usage tracking
  - Token usage and cost estimation
  - Unified approval panel
- Agent execution engine
  - Direct Claude API integration via Anthropic SDK
  - Async/streaming support
  - Token tracking and cost calculation
  - Background agent execution
- Skills system
  - Automatic skill extraction from repetitive patterns
  - Security review for proposed skills
  - Skill management CLI commands
- Agent roles
  - Auditor (governance and security)
  - Planner (task planning)
  - Researcher (technical research)
  - Backend Coder (Python development)
  - Reviewer (code review)
  - Tester (testing and QA)
  - Skill Extractor and Reviewer (meta-agents)

### Changed
- Migrated from pip to uv for package management
  - Removed requirements.txt (using pyproject.toml)
  - Updated install.sh to use uv
  - Faster installation and better dependency resolution
- Dashboard UI localized to Japanese
- tmux monitoring is now optional and separate from dashboard

### Fixed
- Import cycle issues in task dispatcher
- Git command errors in installer

## [0.1.0] - 2025-01-30

### Added
- Initial release
- Hierarchical multi-agent architecture
- Textual TUI dashboard
- tmux-based agent monitoring
- Project configuration system
- Basic CLI commands (init, start, config, roles)
- GitHub repository setup
- MIT License
- Installation script with curl | sh support
