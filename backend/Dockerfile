# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for psycopg2 and potentially other libs)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY backend/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Create directory for data and screenshots
RUN mkdir -p data/screenshots

# Expose port 8765
EXPOSE 8765

# Define environment variables (defaults)
ENV SECRET_KEY="prome-secret-key-change-in-production-2026"
ENV DATABASE_URL="sqlite:///data/prome.db"
ENV GCS_PROJECT_ID=""
ENV GCS_BUCKET_NAME=""
ENV GOOGLE_APPLICATION_CREDENTIALS=""

# Run uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765"]
