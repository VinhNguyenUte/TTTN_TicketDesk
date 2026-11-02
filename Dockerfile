# Dockerfile for TicketDesk Django application
# Uses Python 3.11 slim image
FROM python:3.11-slim

# Install OS dependencies needed for psycopg2 and other packages, plus pg_isready client
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory
WORKDIR /app

# Install pip requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project files
COPY . .

# Change ownership
RUN chown -R appuser:appgroup /app
USER appuser

# Expose port 8000 (Django dev server) – can be overridden in production
EXPOSE 8000

RUN chmod +x /app/entrypoint.sh

# Default command – runs entrypoint script
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

