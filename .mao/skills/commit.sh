#!/bin/bash
set -e

# Parse arguments
CUSTOM_MESSAGE=""
VERSION_TAG=""
UPDATE_CHANGELOG=true
PUSH_TO_REMOTE=true
AUTO_STAGE=true

while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--message)
      CUSTOM_MESSAGE="$2"
      shift 2
      ;;
    -t|--tag)
      VERSION_TAG="$2"
      shift 2
      ;;
    --no-changelog)
      UPDATE_CHANGELOG=false
      shift
      ;;
    --no-push)
      PUSH_TO_REMOTE=false
      shift
      ;;
    -a|--auto-stage)
      AUTO_STAGE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "Error: Not in a git repository"
  exit 1
fi

# Auto-stage files if enabled
if [ "$AUTO_STAGE" = true ]; then
  echo "📝 Staging modified files..."
  git add -u

  # Check for untracked files and ask if they should be added
  UNTRACKED=$(git ls-files --others --exclude-standard)
  if [ -n "$UNTRACKED" ]; then
    echo "⚠️  Untracked files found:"
    echo "$UNTRACKED"
    echo "Add them? (y/n)"
    # For now, skip interactive prompt in skill
    # git add .
  fi
fi

# Check if there are staged changes
if ! git diff --cached --quiet; then
  echo "✅ Changes staged for commit"
else
  echo "❌ No changes staged for commit"
  exit 1
fi

# Generate commit message if not provided
if [ -z "$CUSTOM_MESSAGE" ]; then
  echo "🤖 Analyzing changes..."
  CHANGED_FILES=$(git diff --cached --name-only)
  FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')
  STATS=$(git diff --cached --shortstat)
  CUSTOM_MESSAGE="Update ${FILE_COUNT} files - ${STATS}"
fi

# Create commit
echo "📦 Creating commit..."
COMMIT_MSG="${CUSTOM_MESSAGE}\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git commit -m "${COMMIT_MSG}"

COMMIT_HASH=$(git rev-parse --short HEAD)
echo "✅ Committed: $COMMIT_HASH"

# Update CHANGELOG if enabled
if [ "$UPDATE_CHANGELOG" = true ]; then
  echo "📝 Updating CHANGELOG.md..."
  CHANGELOG_FILE="CHANGELOG.md"
  DATE=$(date +%Y-%m-%d)

  if [ ! -f "$CHANGELOG_FILE" ]; then
    # Create new CHANGELOG
    {
      echo "# Changelog"
      echo ""
      echo "All notable changes to this project will be documented in this file."
      echo ""
      echo "## [Unreleased]"
      echo ""
      if [ -n "$VERSION_TAG" ]; then
        echo "## [$VERSION_TAG] - $DATE"
        echo ""
        echo "### Changed"
        echo "- $(echo "$CUSTOM_MESSAGE" | head -1)"
        echo ""
      fi
    } > "$CHANGELOG_FILE"
  else
    # Insert new entry - TODO: implement proper parsing
    echo "⚠️  CHANGELOG update for existing file not implemented yet"
  fi
fi

# Create version tag if specified
if [ -n "$VERSION_TAG" ]; then
  echo "🏷️  Creating tag: $VERSION_TAG"
  git tag -a "$VERSION_TAG" -m "Release $VERSION_TAG"
  echo "✅ Tag created: $VERSION_TAG"
fi

# Push to remote if enabled
if [ "$PUSH_TO_REMOTE" = true ]; then
  echo "🚀 Pushing to remote..."

  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  git push -u origin "$CURRENT_BRANCH"

  if [ -n "$VERSION_TAG" ]; then
    git push origin "$VERSION_TAG"
  fi

  echo "✅ Pushed to remote"
fi

echo "🎉 Done!"
