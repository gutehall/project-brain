#!/usr/bin/env python3
"""
project-brain MCP Server
Connects Cursor, Warp and other MCP clients to your local RAG pipeline + Ollama.
"""

import asyncio
import json
import sys

# MCP protocol communication via stdio
class MCPServer:
    def __init__(self):
        self.rag = None
        self.tools = self._define_tools()

    def _define_tools(self):
        return [
            {
                "name": "ask_project",
                "description": "Ask a question about the codebase. Uses RAG to find relevant code and answer with full context awareness.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Your question about the project"
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "index_project",
                "description": "Index or update the project codebase in the vector database.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to the project (leave empty to use the configured path)"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force re-indexing even if an index already exists"
                        }
                    }
                }
            },
            {
                "name": "search_code",
                "description": "Search for specific code, functions or patterns in the project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What you are looking for (function, class, concept)"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_project_summary",
                "description": "Get a high-level summary of the project's architecture and structure.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_linear_issue",
                "description": "Create a Linear issue based on a description. AI drafts the title, description and priority automatically.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Describe what the issue is about"
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Linear team ID (optional, uses default from config)"
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "create_linear_project",
                "description": "Create a Linear project. Optionally uses AI to generate a description from the project name and codebase context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Project name"
                        },
                        "description": {
                            "type": "string",
                            "description": "Project description (optional; AI-generated from name if omitted)"
                        },
                        "team_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Team IDs to associate (optional, uses default from config)"
                        }
                    },
                    "required": ["name"]
                }
            }
        ]

    async def handle_request(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "project-brain",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.tools}
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            result = await self.execute_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        # Lazy-load RAG to avoid long startup time
        if self.rag is None:
            from rag_pipeline import RAGPipeline
            self.rag = RAGPipeline()

        if tool_name == "ask_project":
            return await self.rag.ask(args["question"])

        elif tool_name == "index_project":
            path = args.get("project_path")
            force = args.get("force", False)
            return await self.rag.index(project_path=path, force=force)

        elif tool_name == "search_code":
            results = await self.rag.search(args["query"], n=args.get("n_results", 5))
            return results

        elif tool_name == "get_project_summary":
            return await self.rag.get_summary()

        elif tool_name == "create_linear_issue":
            from linear_integration import create_issue
            return await create_issue(
                description=args["description"],
                team_id=args.get("team_id"),
                rag=self.rag
            )

        elif tool_name == "create_linear_project":
            from linear_integration import create_project
            return await create_project(
                name=args["name"],
                description=args.get("description"),
                team_ids=args.get("team_ids"),
                rag=self.rag
            )

        return f"Unknown tool: {tool_name}"

    async def run(self):
        """Run the MCP server via stdio (standard for the MCP protocol)."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        write_transport, write_protocol = await loop.connect_write_pipe(
            asyncio.BaseProtocol, sys.stdout
        )

        buffer = ""
        while True:
            try:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        request = json.loads(line)
                        response = await self.handle_request(request)
                        output = json.dumps(response) + "\n"
                        write_transport.write(output.encode("utf-8"))
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                break


if __name__ == "__main__":
    server = MCPServer()
    asyncio.run(server.run())
