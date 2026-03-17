FROM langflowai/langflow:latest

# Copy custom CrewHub components
COPY components/ /root/.langflow/components/

# Disable auth (CrewHub handles auth via iframe + JWT exchange)
# Disable Python code nodes (security — prevent code injection on shared Space)
ENV LANGFLOW_HOST=0.0.0.0 \
    LANGFLOW_PORT=7860 \
    LANGFLOW_DATABASE_URL=sqlite:///./langflow.db \
    LANGFLOW_LOGIN_ENABLED=False \
    LANGFLOW_AUTO_LOGIN=True \
    LANGFLOW_LOG_LEVEL=INFO \
    LANGFLOW_COMPONENTS_PATH=/root/.langflow/components

EXPOSE 7860

CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
