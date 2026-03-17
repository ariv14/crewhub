FROM langflowai/langflow:latest

USER root

# Create components directory accessible by non-root user (HF runs as uid 1000)
RUN mkdir -p /app/custom_components && chown -R 1000:1000 /app/custom_components

# Copy custom CrewHub components
COPY --chown=1000:1000 components/ /app/custom_components/

# Create writable data directory for Langflow DB
RUN mkdir -p /app/data && chown -R 1000:1000 /app/data

USER 1000

# Disable auth (CrewHub handles auth via iframe + JWT exchange)
ENV LANGFLOW_HOST=0.0.0.0 \
    LANGFLOW_PORT=7860 \
    LANGFLOW_DATABASE_URL=sqlite:////app/data/langflow.db \
    LANGFLOW_LOGIN_ENABLED=False \
    LANGFLOW_AUTO_LOGIN=True \
    LANGFLOW_LOG_LEVEL=INFO \
    LANGFLOW_COMPONENTS_PATH=/app/custom_components

EXPOSE 7860

CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
