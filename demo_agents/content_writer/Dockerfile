FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn httpx litellm google-generativeai
COPY demo_agents/__init__.py demo_agents/__init__.py
COPY demo_agents/base.py demo_agents/base.py
COPY demo_agents/content_writer/__init__.py demo_agents/content_writer/__init__.py
COPY demo_agents/content_writer/agent.py demo_agents/content_writer/agent.py
USER 1000
ENV PORT=7860
EXPOSE 7860
CMD ["uvicorn", "demo_agents.content_writer.agent:app", "--host", "0.0.0.0", "--port", "7860"]
