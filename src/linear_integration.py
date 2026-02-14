"""
Linear Integration for project-brain
Creates Linear issues using AI based on free-text descriptions.
"""

import json
import httpx

from config import load_config


async def create_issue(description: str, team_id: str = None, rag=None) -> str:
    """
    Create a Linear issue based on a free-text description.
    AI automatically drafts the title, description and priority.
    """
    config = load_config()
    api_key = config.get("linear_api_key", "")
    default_team = team_id or config.get("linear_team_id", "")

    if not api_key:
        return (
            "❌ Linear API key is missing.\n"
            "Add 'linear_api_key' to config/config.json\n"
            "Get your key at: https://linear.app/settings/api"
        )

    if not default_team:
        return (
            "❌ Linear Team ID is missing.\n"
            "Add 'linear_team_id' to config/config.json\n"
            "Find your team ID via Linear's API or URL."
        )

    # Fetch project context if RAG is available
    project_context = ""
    if rag:
        try:
            summary_data = rag._load_json(rag._summary_file, {})
            project_context = summary_data.get("summary", "")[:500]
        except Exception:
            pass

    # Let Ollama draft the issue
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    llm_model = config.get("llm_model", "deepseek-coder-v2")

    prompt = f"""You are a project manager. Create a Linear issue based on the following description.
Respond ONLY with valid JSON, nothing else.

Project context: {project_context}

Description: {description}

Return JSON with these fields:
{{
  "title": "Short, clear title (max 80 characters)",
  "description": "Detailed description with background, acceptance criteria and any technical details",
  "priority": 0-4 where 0=none, 1=urgent, 2=high, 3=medium, 4=low,
  "labelName": "Bug | Feature | Improvement | Documentation | Refactor"
}}"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": llm_model, "prompt": prompt, "stream": False}
            )
            raw = resp.json()["response"]

            # Extract JSON from the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            issue_data = json.loads(raw[start:end])

    except Exception as e:
        return f"❌ Could not generate issue data: {e}"

    # Create issue via Linear GraphQL API
    mutation = """
    mutation CreateIssue($title: String!, $description: String, $teamId: String!, $priority: Int) {
      issueCreate(input: {
        title: $title
        description: $description
        teamId: $teamId
        priority: $priority
      }) {
        success
        issue {
          id
          identifier
          title
          url
        }
      }
    }
    """

    variables = {
        "title": issue_data.get("title", description[:80]),
        "description": issue_data.get("description", description),
        "teamId": default_team,
        "priority": issue_data.get("priority", 3)
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json"
                }
            )
            result = resp.json()

            if "errors" in result:
                return f"❌ Linear API error: {result['errors']}"

            issue = result["data"]["issueCreate"]["issue"]
            return (
                f"✅ Linear issue created!\n"
                f"   ID: {issue['identifier']}\n"
                f"   Title: {issue['title']}\n"
                f"   Link: {issue['url']}\n\n"
                f"📝 AI-generated description:\n{variables['description'][:300]}..."
            )

    except Exception as e:
        return f"❌ Could not create Linear issue: {e}"


async def create_project(name: str, description: str = None, team_ids: list[str] = None, rag=None) -> str:
    """
    Create a Linear project. Optionally uses AI to expand a short name into a full description.
    """
    config = load_config()
    api_key = config.get("linear_api_key", "")
    default_team_ids = team_ids or ([config.get("linear_team_id")] if config.get("linear_team_id") else [])

    if not api_key:
        return (
            "❌ Linear API key is missing.\n"
            "Add 'linear_api_key' to config/config.json\n"
            "Get your key at: https://linear.app/settings/api"
        )

    # If no description provided, use AI to generate one from the name
    if not description and rag:
        try:
            ollama_url = config.get("ollama_url", "http://localhost:11434")
            llm_model = config.get("llm_model", "deepseek-coder-v2")
            summary_data = rag._load_json(rag._summary_file, {})
            project_context = summary_data.get("summary", "")[:300]

            prompt = f"""Based on this project name, write a 1-2 sentence description for a Linear project.
Project context: {project_context}
Name: {name}
Respond with ONLY the description, no quotes or JSON."""

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": llm_model, "prompt": prompt, "stream": False}
                )
                description = resp.json().get("response", "").strip().strip('"')
        except Exception:
            description = ""

    variables = {
        "name": name[:255],
        "description": description or None,
        "teamIds": [t for t in default_team_ids if t] or None
    }

    mutation = """
    mutation ProjectCreate($name: String!, $description: String, $teamIds: [String!]) {
      projectCreate(input: {
        name: $name
        description: $description
        teamIds: $teamIds
      }) {
        success
        project {
          id
          name
          description
          url
          state
        }
      }
    }
    """

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json"
                }
            )
            result = resp.json()

            if "errors" in result:
                return f"❌ Linear API error: {result['errors']}"

            project = result["data"]["projectCreate"]["project"]
            return (
                f"✅ Linear project created!\n"
                f"   Name: {project['name']}\n"
                f"   State: {project['state']}\n"
                f"   Link: {project['url']}\n"
                + (f"\n📝 Description: {project.get('description', '')[:200]}" if project.get("description") else "")
            )

    except Exception as e:
        return f"❌ Could not create Linear project: {e}"
