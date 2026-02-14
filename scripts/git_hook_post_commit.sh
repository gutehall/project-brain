#!/bin/bash
# Git post-commit hook — automatically re-indexes the project after each commit
#
# Installation: copy to your project's .git/hooks/post-commit
#   cp scripts/git_hook_post_commit.sh /your-project/.git/hooks/post-commit && chmod +x /your-project/.git/hooks/post-commit
#
# IMPORTANT: Edit PROJECT_BRAIN_DIR below to match your project-brain install path.

PROJECT_BRAIN_DIR="$HOME/project-brain"

# Only run if project-brain is installed
if [ ! -f "$PROJECT_BRAIN_DIR/scripts/brain.py" ]; then
    exit 0
fi

# Run indexing in the background (does not block the commit)
echo "project-brain: updating index in the background..."
(
    cd "$PROJECT_BRAIN_DIR"
    source .venv/bin/activate 2>/dev/null
    python3 scripts/brain.py index > /tmp/project-brain-index.log 2>&1
    echo "project-brain index updated"
) &

exit 0
