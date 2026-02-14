# ─────────────────────────────────────────────
# project-brain — Warp/terminal aliases
# Add this file to your .zshrc with:
#   source ~/project-brain/config/warp_aliases.sh
# ─────────────────────────────────────────────

# Auto-detect project-brain directory from this script's location
export PROJECT_BRAIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# Activate virtual environment and run CLI
brain() {
    (
        cd "$PROJECT_BRAIN_DIR"
        source .venv/bin/activate 2>/dev/null
        python3 scripts/brain.py "$@"
    )
}

# Shorthand commands
alias brain-ask='brain ask'
alias brain-search='brain search'
alias brain-index='brain index'
alias brain-summary='brain summary'
alias brain-linear='brain linear'
alias brain-linear-project='brain linear-project'

# Autocomplete (zsh)
_brain_complete() {
    local commands=("ask" "search" "index" "summary" "linear" "linear-project")
    compadd -a commands
}
compdef _brain_complete brain

# ─────────────────────────────────────────────
# Usage in Warp:
#   brain ask "How does the login flow work?"
#   brain search "API endpoints"
#   brain index                    # index project
#   brain index --force            # force re-indexing
#   brain summary                  # show project overview
#   brain linear "Fix crash when user logs out"
#   brain linear-project "Q1 Migration" "Migrate legacy API to v2"
# ─────────────────────────────────────────────
