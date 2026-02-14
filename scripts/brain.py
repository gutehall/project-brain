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
import logging
import os
import sys

# Locate the project's src directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "..", "src")
sys.path.insert(0, SRC_DIR)

# Ensure we run from the right directory for config
os.chdir(os.path.join(SCRIPT_DIR, ".."))


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr, force=True)
    logging.getLogger("project-brain").setLevel(level)


async def main():
    argv = sys.argv[1:]
    verbose = "-v" in argv or "--verbose" in argv
    quiet = "-q" in argv or "--quiet" in argv
    argv = [a for a in argv if a not in ("-v", "--verbose", "-q", "--quiet")]

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("\nOptions: -v/--verbose  -q/--quiet  -h/--help")
        sys.exit(0)

    setup_logging(verbose=verbose, quiet=quiet)

    command = argv[0].lower()
    args = argv[1:]

    from rag_pipeline import RAGPipeline
    rag = RAGPipeline()

    if command in ("ask", "a"):
        if not args:
            print("Usage: brain ask <question>")
            sys.exit(1)
        question = " ".join(args)
        print(f"\nAsking about the project: {question}\n")
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
        args = [a for a in args if a not in ("--force", "-f")]
        if not quiet:
            print("Indexing project...\n")
        result = await rag.index(force=force)
        print(result)

    elif command in ("summary", "sum"):
        result = await rag.get_summary()
        print("\nProject Overview\n")
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
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Available commands: ask, search, index, summary, linear, linear-project", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
