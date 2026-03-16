FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn httpx litellm

# Preserve module structure: demo_agents.base, demo_agents.marketing.*
COPY demo_agents/__init__.py demo_agents/__init__.py
COPY demo_agents/base.py demo_agents/base.py
COPY demo_agents/marketing/__init__.py demo_agents/marketing/__init__.py
COPY demo_agents/marketing/marketing_agent.py demo_agents/marketing/marketing_agent.py
COPY demo_agents/marketing/division_loader.py demo_agents/marketing/division_loader.py
COPY demo_agents/marketing/divisions/ demo_agents/marketing/divisions/

USER 1000

ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "demo_agents.marketing.marketing_agent:app", "--host", "0.0.0.0", "--port", "7860"]
