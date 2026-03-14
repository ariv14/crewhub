FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn httpx litellm google-generativeai

# Preserve module structure so imports work: demo_agents.base, demo_agents.creator.agent
COPY demo_agents/__init__.py demo_agents/__init__.py
COPY demo_agents/base.py demo_agents/base.py
COPY demo_agents/creator/__init__.py demo_agents/creator/__init__.py
COPY demo_agents/creator/agent.py demo_agents/creator/agent.py

USER 1000

ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "demo_agents.creator.agent:app", "--host", "0.0.0.0", "--port", "7860"]
