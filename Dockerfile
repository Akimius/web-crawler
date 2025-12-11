FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Chromium
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    libssl-dev \
    curl \
    tzdata \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Set permissions
RUN chmod -R 755 /app

CMD ["python", "main.py"]