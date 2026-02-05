FROM python:3.11-slim

# Install system dependencies including Node.js for yt-dlp signature solving
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Update yt-dlp to latest version to ensure signature solving works
RUN pip install --upgrade yt-dlp

COPY . .

# Run with Gunicorn with longer timeout for downloads
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 app:app
