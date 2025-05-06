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

# Set workdir
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Default port for Render
ENV PORT=10000

# Expose port
EXPOSE 10000

# Start command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
