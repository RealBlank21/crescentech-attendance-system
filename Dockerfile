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

# Set Flask to run in production mode
ENV FLASK_ENV=production

# Expose port 5000
EXPOSE 5000

# Command to run when container starts
CMD ["sh", "-c", "python database_setup.py && python seed_data_2.py && python app.py"]