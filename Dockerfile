FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks and other dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Only needed if using psycopg2 (not binary)
# RUN apt-get update && apt-get install -y \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy src directory instead of app directory
COPY src/ ./src/
COPY run.sh .
RUN chmod +x run.sh

CMD ["bash", "run.sh"]
