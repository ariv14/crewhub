FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy gateway code
COPY . .

# HF Spaces expects port from PORT env var
ENV PORT=7860

EXPOSE ${PORT}

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
