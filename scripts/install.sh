#!/bin/bash
# project-brain install script
# Installs all dependencies and sets up models in Ollama

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BOLD}🧠 project-brain — installing...${RESET}\n"

# --- Check Python ---
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Install Python 3.10+ and try again.${RESET}"
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${RED}Python ${PYTHON_VERSION} found, but 3.10+ is required.${RESET}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${RESET}"

# --- Check Ollama ---
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠ Ollama not found. Installing...${RESET}"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}✓ Ollama is installed${RESET}"
fi

# --- Create virtual environment ---
echo -e "\n${BOLD}Creating Python environment...${RESET}"
python3 -m venv .venv
source .venv/bin/activate

# --- Install Python packages ---
echo -e "\n${BOLD}Installing Python dependencies...${RESET}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo -e "${GREEN}✓ Python dependencies installed${RESET}"

# --- Download Ollama models ---
echo -e "\n${BOLD}Downloading AI models (this will take a few minutes)...${RESET}"

echo "  → Downloading nomic-embed-text (embeddings model, ~300MB)..."
ollama pull nomic-embed-text

echo "  → Downloading deepseek-coder-v2 (LLM, ~9GB — grab a coffee! ☕)..."
ollama pull deepseek-coder-v2

echo -e "${GREEN}✓ Models downloaded${RESET}"

# --- Bootstrap config if missing ---
CONFIG_FILE="config/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Creating config from config.example.json...${RESET}"
    cp config/config.example.json "$CONFIG_FILE"
fi

# --- Expand ~ in config and create DB directory ---
DB_PATH=$(python3 -c "import json,os; c=json.load(open('$CONFIG_FILE')); print(os.path.expanduser(c.get('database_path','~/.project-brain/db')))")
mkdir -p "$DB_PATH"

echo -e "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}Installation complete!${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
echo -e "Next steps:"
echo -e "  ${YELLOW}1.${RESET} Edit ${BOLD}config/config.json${RESET} and set 'project_path'"
echo -e "  ${YELLOW}2.${RESET} Run ${BOLD}./scripts/index.sh${RESET} to index your project"
echo -e "  ${YELLOW}3.${RESET} Copy ${BOLD}config/cursor_mcp.json${RESET} to ${BOLD}~/.cursor/mcp.json${RESET}"
echo -e "  ${YELLOW}4.${RESET} Add aliases to ~/.zshrc from ${BOLD}config/warp_aliases.sh${RESET}\n"
echo -e "Database will be saved to: ${BOLD}${DB_PATH}${RESET}"
