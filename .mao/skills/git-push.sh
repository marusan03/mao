#!/bin/bash
# Git Push Workflow Script
# Arguments: message files tag tag_message remote branch

set -e  # Exit on error

MESSAGE="$1"
FILES="${2:-.}"
TAG="$3"
TAG_MESSAGE="$4"
REMOTE="${5:-origin}"
BRANCH="${6:-main}"

echo "=== Git Push Workflow ==="
echo

# 1. Show current status
echo "📋 Checking git status..."
git status
echo

# 2. Stage files
echo "➕ Adding files: $FILES"
git add "$FILES"
echo

# 3. Show staged changes
echo "📋 Staged changes:"
git status
echo

# 4. Show diff
echo "📝 Changes to be committed:"
git diff --cached --stat
echo

# 5. Commit
echo "💾 Creating commit..."
git commit -m "$MESSAGE

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
echo "✓ Commit created"
echo

# 6. Create tag if specified
if [ -n "$TAG" ]; then
    echo "🏷️  Creating tag: $TAG"
    if [ -n "$TAG_MESSAGE" ]; then
        git tag -a "$TAG" -m "$TAG_MESSAGE"
    else
        git tag -a "$TAG" -m "Release $TAG"
    fi
    echo "✓ Tag created"
    echo
fi

# 7. Push commits
echo "📤 Pushing to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH"
echo "✓ Pushed commits"
echo

# 8. Push tag if created
if [ -n "$TAG" ]; then
    echo "📤 Pushing tag: $TAG"
    git push "$REMOTE" "$TAG"
    echo "✓ Tag pushed"
    echo
fi

echo "✅ Git push workflow completed successfully!"
