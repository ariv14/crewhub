"""CrewHub Publish — metadata node for marketplace publishing."""

from langflow.custom import CustomComponent


class CrewHubPublishComponent(CustomComponent):
    display_name = "CrewHub Publish"
    description = (
        "Mark this flow as publishable to the CrewHub marketplace. "
        "Configure agent name, description, and pricing. "
        "This is a pass-through node — connect it as your final output."
    )
    documentation = "https://crewhubai.com/docs"
    icon = "rocket"

    def build_config(self):
        return {
            "text": {
                "display_name": "Output Text",
                "info": "The final output from your agent flow",
                "required": True,
                "input_types": ["str"],
            },
            "agent_name": {
                "display_name": "Agent Name",
                "info": "Name for your agent on the marketplace",
                "value": "My Custom Agent",
            },
            "agent_description": {
                "display_name": "Description",
                "info": "What does this agent do? (shown on marketplace)",
                "value": "",
                "multiline": True,
            },
            "category": {
                "display_name": "Category",
                "info": "Agent category on the marketplace",
                "options": [
                    "general", "code", "data", "writing", "research",
                    "design", "automation", "security", "finance", "support",
                ],
                "value": "general",
            },
            "credits_per_task": {
                "display_name": "Credits per Task",
                "info": "Credits to charge per task (min 5)",
                "value": 10,
            },
        }

    def build(
        self,
        text: str,
        agent_name: str = "My Custom Agent",
        agent_description: str = "",
        category: str = "general",
        credits_per_task: int = 10,
    ) -> str:
        # Pass-through node — metadata is read by CrewHub
        # when user clicks "Publish to Marketplace"
        return text
