# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create uploads directory and set permissions
RUN mkdir -p static/uploads && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set production environment
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port 8000 (standard for gunicorn)
EXPOSE 8000

# Command to run when container starts
CMD ["sh", "-c", "python database_setup.py && gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 app:app"]
