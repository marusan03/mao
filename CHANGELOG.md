# Changelog

All notable changes to MAO (Multi-Agent Orchestrator) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **MAO Integration Skills - Parallel Execution Support** - Added concurrency safety to prevent data loss and SQLite errors
  - Phase 1 (Critical fixes):
    - `mao-complete`: File locking (`fcntl.flock`) + atomic write operation for `index.json` to completely prevent Lost Update problem
    - Lock file (`.index.lock`) ensures read-modify-write atomicity across processes
    - All skills: Added 30-second SQLite timeout (`timeout=30.0`) to prevent `SQLITE_BUSY` errors
  - Phase 2 (Reliability improvements):
    - All skills: Implemented exponential backoff retry logic (max 3 retries) for database lock contention
    - All skills: Enabled WAL mode (`PRAGMA journal_mode=WAL`) for better read/write concurrency
  - Phase 3 (Optional - Complete safety):
    - `mao-log`: Added file locking using `fcntl` on POSIX systems (macOS, Linux) to prevent log line corruption
    - Windows fallback: Works without file locking (parallel writes are rare for agent-specific logs)
  - **Verified**: 8 agents running in parallel - 100% success rate, zero data loss, zero SQLite errors
  - Affected files: `.mao/skills/mao-complete.yaml`, `.mao/skills/mao-register.yaml`, `.mao/skills/mao-update-status.yaml`, `.mao/skills/mao-log.yaml`
  - Impact: Multiple agents can now safely run in parallel without data corruption or database errors

### Added
- **MAO Integration Skills for Task Agents** - Skills that Claude Code Task agents can use to integrate with MAO
  - `/mao-register` - Register Task agent with MAO's StateManager
  - `/mao-log` - Send logs to MAO's log viewer
  - `/mao-update-status` - Update agent status in dashboard
  - `/mao-complete` - Report completion to approval queue
  - Task agents can now appear in MAO dashboard and output logs
  - CTO instructs Task agents to use these skills for full MAO integration
  - Created comprehensive MAO integration documentation (`mao/roles/_mao_integration.md`)
  - Updated all 8 role prompts to mandate MAO skill usage:
    - `coder_backend.md` - Full detailed integration section with examples
    - `researcher.md` - Simplified integration section
    - `tester.md` - Simplified integration section
    - `reviewer.md` - Simplified integration section
    - `planner.md` - Simplified integration section
    - `skill_extractor.md` - Simplified integration section
    - `skill_reviewer.md` - Simplified integration section
    - `auditor.md` - Simplified integration section
- **Agent Lifecycle Management** - Automatic cleanup of agent resources
  - Phase 1: Cleanup on task approval
    - Deletes agent state from StateManager
    - Removes worktree if exists
    - Clears approval queue item
  - Phase 2: Cleanup on task rejection
    - Clears previous agent state before retry
    - Removes previous worktree
    - Prevents memory leaks from retry cycles
  - Phase 3: Comprehensive cleanup on session exit
    - Warns about pending approvals
    - Clears all agent states
    - Cleans up all worktrees
    - Clears task queue and approval queue
  - Async callback support in ApprovalQueueWidget
  - Logs are preserved for debugging and audit trail
- **HTTP API Module** - RESTful API endpoints for external integrations
  - Contact form API endpoint (`POST /api/v1/contact`)
  - Input validation using Pydantic models
  - File-based storage backend in `.mao/contact_forms/`
  - Interactive API documentation at `/docs` (Swagger UI)
  - `mao-api` CLI command to start the API server
  - FastAPI and Uvicorn dependencies
  - Comprehensive test script (`examples/test_contact_api.py`)
  - API documentation in `mao/api/README.md`
  - Support for retrieving and listing submissions
  - Proper error handling and HTTP status codes
- **CLAUDE.md** - Developer guide for Claude Code
  - Quick start guide for AI development assistants working on MAO
  - Navigation map for documentation structure
  - Task-based documentation recommendations
  - Development workflow and rules reference
  - Links to DEVELOPMENT_RULES.md and other key documents
- **Feedback system repair command** - `mao feedback repair`
  - Automatically repairs index.json by scanning individual feedback files
  - Detects and adds missing entries

### Fixed
- **CTO Chat display issue with Silent Exception handling**
  - Root cause: `refresh_display()` in `cto_chat.py` had silent exception handling (`except Exception: pass`) that was hiding `NoActiveAppError`
  - Symptom: Messages were added internally but not displayed on screen
  - Fix: Proper `NoActiveAppError` handling - skip UI update when App context unavailable, log actual errors
  - Added comprehensive debug logging to trace message flow (`add_cto_message`, `append_streaming_chunk`, `complete_streaming_message`, `refresh_display`)
  - Added debug logging to dashboard CTO response handling
  - Created test scripts: `scripts/test_cto_chat_widget.py` (unit test), `scripts/test_cto_integration.py` (integration test)
  - Now properly distinguishes between "App not available" (normal in tests) vs actual errors
- **CTO Task agents not integrating with MAO (CRITICAL fix)**
  - Root cause: Task agents had no way to communicate with MAO's StateManager and logging systems
  - Symptoms: CTO uses Task tool, but agents don't appear in Agent List or logs
  - Solution: Created MAO integration skills that Task agents use to register, log, update status, and report completion
  - Updated cto_prompt.md to instruct agents to use MAO integration skills
  - Now Task agents properly integrate with MAO dashboard and logging
- **Agent count statistics includes other sessions (CRITICAL fix)**
  - Root cause: `StateManager.get_stats()` was not filtering by session_id
  - Symptoms: Agent count shows 1 on startup (from previous session), becomes 2 when CTO starts
  - Other sessions' agents were incorrectly counted in statistics
  - Fixed by adding session_id filtering to `get_stats()` method
  - Now only counts agents from current session
- **Agent startup failure in tmux (CRITICAL fix)**
  - Root cause: tmux_manager.py was using incorrect command `claude-code` instead of `claude`
  - Agents were not starting because command was not found in PATH
  - Symptoms: CTO says agents are starting, but they don't appear in Agent List
  - Fixed by replacing all `claude-code` references with `claude` in tmux_manager.py
  - Now agents correctly start and appear in dashboard
- **Session isolation for agents (CRITICAL fix)**
  - Agents from different sessions were visible to each other
  - Root cause: StateManager didn't filter by session_id
  - Fixed by adding session_id parameter to StateManager:
    - Agent states now keyed as `{session_id}:{agent_id}`
    - get_all_states() filters by current session
    - Each session sees only its own agents
  - Modified files:
    - mao/orchestrator/state_manager.py: Added session_id support
    - mao/ui/dashboard_interactive.py: Pass session_id to StateManager
- **ApprovalQueueWidget AttributeError**
  - Fixed: 'ApprovalQueueWidget' object has no attribute 'add_agent_approval'
  - dashboard_interactive.py:1149 was calling non-existent method
  - Now correctly creates ApprovalRequest object and calls add_request()
  - Fixes agent completion approval workflow
- **Feedback system index.json inconsistency bug**
  - Fixed race condition where individual feedback files were created but not added to index.json
  - Implemented atomic write operations using temporary files and os.replace()
  - Added transaction-like behavior with rollback on failure
  - Individual files are now written first, then index.json is updated
  - If index.json update fails, individual files are rolled back
  - Repaired existing inconsistencies: 2 missing feedbacks added to index
- **CTO role not actually executing tasks (CRITICAL bug fix)**
  - CTO was outputting YAML task plans but NOT calling the Task tool to start agents
  - Users were misled into thinking agents were running when they weren't
  - Fixed by updating `mao/agents/cto_prompt.md` with explicit instructions:
    - Added "CRITICAL REQUIREMENT" section at the top emphasizing tool execution
    - Clarified 2-step process: (1) Output YAML plan, (2) Call Task tool for each subtask
    - Updated both examples (Example 1 & 2) to show Task tool execution
    - Added "Task Tool Execution" section in Important Guidelines
    - Added reminder in Summary section
- **CTO agents not executing in parallel (CRITICAL fix)**
  - Agents were starting sequentially instead of in parallel
  - Root cause: CTO was making Task tool calls one at a time (waiting between calls)
  - Fixed by adding explicit parallel execution instructions to `mao/agents/cto_prompt.md`:
    - Added "CRITICAL FOR PARALLEL EXECUTION" warning in Step 2
    - Emphasized: "Make ALL Task tool calls in a SINGLE response"
    - Updated both examples to show all tools called in ONE message
    - Added reminder in Summary section
  - Now agents will execute in parallel as intended
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
