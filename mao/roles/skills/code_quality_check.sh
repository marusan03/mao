#!/usr/bin/env bash
# Code quality check skill - wrapper for easy agent execution
# This script can be called by agents to check code quality

# Get the project root (assumes this script is in mao/roles/skills/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

# Run the main quality check script
exec ./scripts/check_code_quality.sh "$@"
