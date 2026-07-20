FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && (command -v node >/dev/null 2>&1 || ln -sf /usr/bin/nodejs /usr/local/bin/node)

# Deno: noviji yt-dlp zahteva JS runtime za YouTube potpise, a spotdl-ov interni
# yt-dlp trazi bas deno ("Some YouTube downloads require Deno"). Instalira se u
# /usr/local/bin/deno; install skripta sama detektuje arhitekturu (x86_64/aarch64).
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt



COPY . .

RUN mkdir -p /app/downloads /root/.spotdl \
    && cp /app/spotdl_config.json /root/.spotdl/config.json 2>/dev/null || true

# Default port; download folder mora biti isti kao volume mount u docker run (-v ...:/app/downloads)
ENV PORT=5000
ENV DOWNLOAD_DIR=/app/downloads
# Bez ovoga se print() poruke iz app.py ne vide u docker logs (stdout buffering)
ENV PYTHONUNBUFFERED=1
EXPOSE 5000

# Run with Gunicorn with longer timeout for downloads
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 app:app
