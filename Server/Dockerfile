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

# Update yt-dlp to absolute latest version (nightly) for best YouTube compatibility
RUN pip install --upgrade "yt-dlp[default]" && yt-dlp --version

COPY . .

# Default port
ENV PORT=5000
EXPOSE 5000

# Run with Gunicorn with longer timeout for downloads
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 app:app
