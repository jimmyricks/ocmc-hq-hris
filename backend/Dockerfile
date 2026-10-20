# Backend Docker image — FastAPI / Uvicorn on port 8005
FROM python:3.12-slim

WORKDIR /app

# Install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app/ app/

# Ensure uploads directory exists for file storage.
RUN mkdir -p uploads

# Environment variables with sensible defaults.
ENV PYTHONUNBUFFERED=1
ENV PORT=8005
ENV HOST=0.0.0.0

EXPOSE 8005

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
