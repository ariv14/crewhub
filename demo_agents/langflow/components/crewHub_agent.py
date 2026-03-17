"""CrewHub Agent — delegate tasks to marketplace agents."""

import os
import time

from langflow.custom import CustomComponent


class CrewHubAgentComponent(CustomComponent):
    display_name = "CrewHub Agent"
    description = "Delegate a task to a CrewHub marketplace agent and get the result."
    documentation = "https://crewhubai.com/docs"
    icon = "bot"

    def build_config(self):
        return {
            "agent_id": {
                "display_name": "Agent ID",
                "info": "UUID of the CrewHub marketplace agent",
                "required": True,
            },
            "skill_id": {
                "display_name": "Skill ID",
                "info": "UUID of the agent's skill to invoke",
                "required": True,
            },
            "message": {
                "display_name": "Message",
                "info": "Task message to send to the agent",
                "required": True,
                "input_types": ["str"],
            },
            "timeout": {
                "display_name": "Timeout (seconds)",
                "info": "Max wait time for agent response",
                "value": 30,
                "advanced": True,
            },
        }

    def build(
        self,
        agent_id: str,
        skill_id: str,
        message: str,
        timeout: int = 30,
    ) -> str:
        import httpx

        api_url = os.environ.get("CREWHUB_API_URL", "https://api.crewhubai.com")
        api_key = os.environ.get("CREWHUB_AGENT_TOKEN", "")

        if not api_key:
            return "Error: CREWHUB_AGENT_TOKEN not set"

        with httpx.Client(timeout=timeout) as client:
            # Create task
            resp = client.post(
                f"{api_url}/api/v1/tasks/",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json={
                    "provider_agent_id": agent_id,
                    "skill_id": skill_id,
                    "messages": [{"role": "user", "content": message}],
                },
            )
            if resp.status_code not in (200, 201):
                return f"Error creating task: {resp.status_code} {resp.text[:200]}"

            task = resp.json()
            task_id = task.get("id")
            if not task_id:
                return "Error: no task ID in response"

            # Poll for completion
            deadline = time.time() + timeout
            while time.time() < deadline:
                status_resp = client.get(
                    f"{api_url}/api/v1/tasks/{task_id}",
                    headers={"X-API-Key": api_key},
                )
                if status_resp.status_code != 200:
                    time.sleep(2)
                    continue

                task_data = status_resp.json()
                status = task_data.get("status", "")

                if status == "completed":
                    for artifact in task_data.get("artifacts", []):
                        for part in artifact.get("parts", []):
                            text = part.get("text") or part.get("content") or ""
                            if text:
                                return text
                    return "Task completed but no output found."

                if status == "failed":
                    return f"Task failed: {task_data.get('error', 'unknown error')}"

                time.sleep(2)

            return "Task timed out waiting for agent response."
