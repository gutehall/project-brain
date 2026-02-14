#!/usr/bin/env python3
"""
CLI for project-brain — use directly in Warp/terminal.
Add the path to this script to your PATH or use the aliases in warp_aliases.sh.

Usage:
  brain ask "How does authentication work?"
  brain search "stripe webhook"
  brain index
  brain index --force
  brain summary
  brain linear <issue description>
  brain linear-project <project name> [description]
"""

import asyncio
import sys
import os

# Locate the project's src directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "..", "src")
sys.path.insert(0, SRC_DIR)

# Ensure we run from the right directory for config
os.chdir(os.path.join(SCRIPT_DIR, ".."))


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    from rag_pipeline import RAGPipeline
    rag = RAGPipeline()

    if command in ("ask", "a"):
        if not args:
            print("Usage: brain ask <question>")
            sys.exit(1)
        question = " ".join(args)
        print(f"\n🧠 Asking about the project: {question}\n")
        print("─" * 50)
        result = await rag.ask(question)
        print(result)

    elif command in ("search", "s"):
        if not args:
            print("Usage: brain search <query>")
            sys.exit(1)
        query = " ".join(args)
        result = await rag.search(query)
        print(result)

    elif command in ("index", "i"):
        force = "--force" in args or "-f" in args
        print("📂 Indexing project...\n")
        result = await rag.index(force=force)
        print(result)

    elif command in ("summary", "sum"):
        result = await rag.get_summary()
        print("\n📋 Project Overview\n")
        print("─" * 50)
        print(result)

    elif command == "linear":
        if not args:
            print("Usage: brain linear <issue description>")
            sys.exit(1)
        description = " ".join(args)
        from linear_integration import create_issue
        result = await create_issue(description, rag=rag)
        print(result)

    elif command in ("linear-project", "linearproject", "lp"):
        if not args:
            print("Usage: brain linear-project <project name> [description]")
            sys.exit(1)
        name = args[0]
        description = " ".join(args[1:]) if len(args) > 1 else None
        from linear_integration import create_project
        result = await create_project(name, description=description, rag=rag)
        print(result)

    else:
        print(f"Unknown command: {command}")
        print("Available commands: ask, search, index, summary, linear, linear-project")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
