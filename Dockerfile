FROM python:3.11-slim

# Install system dependencies for WeasyPrint, audio, and OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        ffmpeg \
        tesseract-ocr \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set PORT environment variable for Railway
ENV PORT=10000

# Set path where credentials will be written
ENV CREDENTIALS_PATH="/app/gcloud_creds.json"

# Expose the port
EXPOSE 10000

# Start command (write JSON string from env var to file, then run app)
CMD sh -c "\
echo \"$GCLOUD_CREDS_B64\" | base64 -d > $CREDENTIALS_PATH && \
export GOOGLE_APPLICATION_CREDENTIALS=$CREDENTIALS_PATH && \
uvicorn app:app --host 0.0.0.0 --port $PORT"
